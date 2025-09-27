"""Linus-style core data structures."""

import hashlib
import re
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .scip import SCIPSymbolManager


# 专用异常类 - 明确的错误分类
class FileEditError(Exception):
    """文件编辑操作的基础异常"""
    pass


class AtomicWriteError(FileEditError):
    """原子写入失败异常"""
    pass


class FileLockError(FileEditError):
    """文件锁定异常"""
    pass


class ContentMismatchError(FileEditError):
    """内容不匹配异常"""
    pass


@dataclass
class FileInfo:
    language: str
    line_count: int
    symbols: Dict[str, List[str]]
    imports: List[str]
    exports: List[str] = field(default_factory=list)


@dataclass
class SymbolInfo:
    type: str
    file: str
    line: int
    signature: Optional[str] = None
    called_by: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


@dataclass
class SearchQuery:
    pattern: str
    type: str = "text"
    file_pattern: Optional[str] = None
    case_sensitive: bool = True
    limit: Optional[int] = 1000  # Phase 3: 早期退出优化 - 默认最大1000结果


@dataclass
class SearchResult:
    matches: List[Dict[str, Any]]
    total_count: int
    search_time: float


@dataclass
class ImmutableEdit:
    """不可变编辑操作 - Linus风格: 数据即真理"""

    file_path: str
    old_hash: str  # 文件内容hash，避免内容比较
    new_content: str
    operation_id: int = 0
    timestamp: float = field(default_factory=time.time)


# 全局文件锁管理 - 可预测的锁生命周期管理
import threading
import time
from collections import OrderedDict

class ReliableFileLockManager:
    """可靠的文件锁管理器 - 确定性清理，无GC依赖"""

    def __init__(self, max_locks: int = 1000, cleanup_interval: float = 300.0):
        self._locks: OrderedDict[str, threading.Lock] = OrderedDict()
        self._access_times: Dict[str, float] = {}
        self._mutex = threading.Lock()
        self._max_locks = max_locks
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def get_lock(self, file_path: str) -> threading.Lock:
        """获取文件锁 - 线程安全 + 确定性清理"""
        with self._mutex:
            current_time = time.time()

            # 定期清理（确定性触发）
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_locks(current_time)
                self._last_cleanup = current_time

            # 获取或创建锁
            if file_path in self._locks:
                # 更新访问时间并移到最后（LRU）
                lock = self._locks.pop(file_path)
                self._locks[file_path] = lock
                self._access_times[file_path] = current_time
                return lock

            # 如果超过容量，删除最老的
            if len(self._locks) >= self._max_locks:
                oldest_file = next(iter(self._locks))
                del self._locks[oldest_file]
                self._access_times.pop(oldest_file, None)

            # 创建新锁
            lock = threading.Lock()
            self._locks[file_path] = lock
            self._access_times[file_path] = current_time
            return lock

    def _cleanup_old_locks(self, current_time: float):
        """安全清理 - 只清理未被使用的锁"""
        cutoff_time = current_time - self._cleanup_interval
        to_remove = []

        # 检查锁状态，只清理未被占用的锁
        for path, access_time in list(self._access_times.items()):
            if access_time < cutoff_time:
                lock = self._locks.get(path)
                if lock and not lock.locked():  # 确认锁未被占用
                    to_remove.append(path)

        # 安全删除
        for path in to_remove:
            self._locks.pop(path, None)
            self._access_times.pop(path, None)

_reliable_lock_manager = ReliableFileLockManager()

def _get_file_lock(file_path: str) -> threading.Lock:
    """获取文件锁 - 可预测的生命周期管理"""
    return _reliable_lock_manager.get_lock(file_path)


@dataclass
class CodeIndex:
    base_path: str
    files: Dict[str, FileInfo]
    symbols: Dict[str, SymbolInfo]
    scip_manager: Optional["SCIPSymbolManager"] = None  # SCIP协议支持
    _operation_counter: int = field(default=0, init=False, repr=False)
    _counter_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self):
        """初始化SCIP管理器 - Linus风格：简单直接"""
        if self.scip_manager is None:
            from .scip import create_scip_manager, integrate_with_code_index

            self.scip_manager = create_scip_manager(self.base_path)
            integrate_with_code_index(self, self.scip_manager)

    def search(self, query: SearchQuery) -> SearchResult:
        from .search_optimized import OptimizedSearchEngine

        return OptimizedSearchEngine(self).search(query)

    def find_symbol(self, name: str) -> List[Dict[str, Any]]:
        return self.search(SearchQuery(pattern=name, type="symbol")).matches

    def add_file(self, file_path: str, file_info: FileInfo):
        self.files[file_path] = file_info

    def add_symbol(self, symbol_name: str, symbol_info: SymbolInfo):
        self.symbols[symbol_name] = symbol_info

    def get_file(self, file_path: str) -> Optional[FileInfo]:
        return self.files.get(file_path)

    def get_symbol(self, symbol_name: str) -> Optional[SymbolInfo]:
        return self.symbols.get(symbol_name)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "file_count": len(self.files),
            "symbol_count": len(self.symbols),
            "base_path": self.base_path,
        }

    def find_files_by_pattern(self, pattern: str) -> List[str]:
        import fnmatch

        return [path for path in self.files.keys() if fnmatch.fnmatch(path, pattern)]

    def update_incrementally(self, root_path: Optional[str] = None) -> Dict[str, int]:
        """增量更新索引 - Linus原则: 只处理变更文件"""
        from .incremental import get_incremental_indexer

        return get_incremental_indexer().update_index(root_path or self.base_path)

    def force_update_file(self, file_path: str) -> bool:
        """强制更新指定文件 - 忽略变更检测"""
        from .incremental import get_incremental_indexer

        return get_incremental_indexer().force_update_file(file_path)

    def get_changed_files(self) -> List[str]:
        """获取变更文件列表 - 诊断工具"""
        from .incremental import get_incremental_indexer

        return get_incremental_indexer().get_changed_files()

    def remove_file(self, file_path: str) -> None:
        """移除文件索引 - 统一接口"""
        self.files.pop(file_path, None)
        # 移除相关符号
        symbols_to_remove = [
            symbol_name
            for symbol_name, symbol_info in self.symbols.items()
            if symbol_info.file == file_path
        ]
        for symbol_name in symbols_to_remove:
            self.symbols.pop(symbol_name, None)

        # ===== Linus风格文件编辑接口 - Good Taste: 简单可靠 =====

    def _get_next_operation_id(self) -> int:
        """线程安全的操作ID生成器"""
        with self._counter_lock:
            self._operation_counter += 1
            return self._operation_counter

    def _hash_content(self, content: str) -> str:
        """统一的内容hash计算 - 完整hash+文件大小"""
        file_size = len(content.encode())
        hash_full = hashlib.sha256(content.encode()).hexdigest()
        return f"{hash_full}:{file_size}"

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件hash - 使用统一方法"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            return self._hash_content(content)
        except Exception:
            return "missing:0"

    @contextmanager
    def _file_lock_context(self, file_path: str):
        """文件锁上下文管理器 - 防御性编程"""
        file_lock = _get_file_lock(file_path)
        lock_acquired = False

        try:
            lock_acquired = file_lock.acquire(blocking=False)
            if not lock_acquired:
                raise FileLockError(f"File {file_path} is being edited by another operation")
            yield
        finally:
            if lock_acquired:
                try:
                    file_lock.release()
                except RuntimeError:  # 已经释放的锁
                    pass

    def edit_file_atomic(
        self, file_path: str, old_content: str, new_content: str
    ) -> Tuple[bool, Optional[str]]:
        """单文件原子性编辑 - 线程安全实现"""
        try:
            with self._file_lock_context(file_path):
                # 1. 读取当前文件内容
                path_obj = Path(file_path)
                if not path_obj.exists():
                    return False, f"File not found: {file_path}"

                try:
                    current_content = path_obj.read_text(encoding="utf-8")
                except UnicodeDecodeError as e:
                    return False, f"File encoding error: {e}"
                except PermissionError:
                    return False, f"Permission denied: {file_path}"

                # 2. 简单内容匹配和替换
                final_content = self._simple_content_replace(current_content, old_content, new_content)
                if final_content is None:
                    raise ContentMismatchError(f"Cannot find old_content in file: {file_path}")

                # 3. 真正的原子性写入
                return self._write_file_atomic(file_path, final_content)

        except ContentMismatchError as e:
            return False, str(e)
        except FileLockError as e:
            return False, str(e)
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            import traceback
            return False, f"Unexpected error in edit_file_atomic: {e}\nTraceback: {traceback.format_exc()}"

    def edit_files_atomic(self, edits: List[ImmutableEdit]) -> Tuple[bool, Optional[str]]:
        """多文件原子性编辑 - 避免死锁的实现"""
        acquired_locks = []

        try:
            # 1. 按路径排序避免死锁
            sorted_edits = sorted(edits, key=lambda e: e.file_path)

            # 2. 原子性获取所有文件锁
            for edit in sorted_edits:
                file_lock = _get_file_lock(edit.file_path)
                if not file_lock.acquire(blocking=False):
                    return False, f"File is being edited by another process: {edit.file_path}. Please wait for the other operation to complete or check if the file is open in an editor."
                acquired_locks.append(file_lock)

            # 3. 验证所有文件状态
            for edit in sorted_edits:
                current_hash = self._calculate_file_hash(edit.file_path)
                if current_hash != edit.old_hash:
                    return False, f"File {edit.file_path} content changed since hash: {edit.old_hash}"

            # 4. 批量原子性写入
            for edit in sorted_edits:
                success, error = self._write_file_atomic(edit.file_path, edit.new_content)
                if not success:
                    return False, f"Failed to write {edit.file_path}: {error}"

            return True, None

        finally:
            # 5. 按逆序释放锁 - 避免死锁
            for lock in reversed(acquired_locks):
                try:
                    lock.release()
                except RuntimeError:  # 只捕获"锁未获取"异常
                    pass  # 锁已释放或未获取

    def edit_files_transaction(
        self, edits: List[ImmutableEdit]
    ) -> Tuple[bool, Optional[str]]:
        """向后兼容接口 - 重定向到无锁实现"""
        return self.edit_files_atomic(edits)

    def _write_file_atomic(self, file_path: str, content: str) -> Tuple[bool, Optional[str]]:
        """真正的跨平台原子性文件写入 - 文件锁 + 备份恢复"""
        path_obj = Path(file_path)
        temp_file = path_obj.with_suffix(path_obj.suffix + '.tmp')
        backup_path = None

        try:
            # 1. 创建备份
            backup_success, backup_path, backup_error = self._create_backup(path_obj)
            if not backup_success:
                return False, f"Backup creation failed: {backup_error}"

            # 2. 写入临时文件
            temp_file.write_text(content, encoding="utf-8")

            # 3. 跨平台安全的原子替换
            success = self._atomic_replace(temp_file, path_obj)
            if not success:
                # 替换失败，从备份恢复
                if backup_path:
                    try:
                        shutil.copy2(backup_path, path_obj)
                        return False, "Atomic replace failed, file restored from backup"
                    except Exception as e:
                        return False, f"Atomic replace failed AND backup restore failed: {e}"
                else:
                    return False, "Atomic replace failed, no backup was created"

            # 4. 更新索引 - 异步执行，不阻塞编辑
            try:
                self._update_file_in_index(file_path)
            except Exception:
                pass  # 索引更新失败不影响文件编辑

            return True, None

        except PermissionError as e:
            return False, f"File locked or permission denied: {e}"
        except OSError as e:
            return False, f"Write failed: {e}"
        except Exception as e:
            import traceback
            return False, f"Unexpected error in _write_file_atomic: {e}\nTraceback: {traceback.format_exc()}"
        finally:
            # 清理临时文件
            try:
                temp_file.unlink()
            except FileNotFoundError:
                pass  # 已经被移动
            except PermissionError:
                pass  # Windows文件锁定 - 不阻塞

    def _atomic_replace(self, temp_file: Path, target_file: Path) -> bool:
        """跨平台原子性替换 - 最大努力原子性"""
        if sys.platform == 'win32':
            # Windows: 使用多次重试的方式处理文件锁定
            max_retries = 5  # 经验值：处理病毒扫描器和文件锁定
            base_delay = 0.01  # 基础延迟10ms，避免CPU spinning
            for i in range(max_retries):
                try:
                    # 检查目标文件是否存在
                    if target_file.exists():
                        target_file.unlink()
                    temp_file.rename(target_file)
                    return True
                except PermissionError as e:
                    if i == max_retries - 1:
                        # 最后一次重试失败，抛出详细异常
                        raise PermissionError(f"File locked after {max_retries} retries: {target_file}. Check if file is open in another program or being scanned by antivirus. Original error: {e}")
                    # 指数退避重试
                    time.sleep(base_delay * (2 ** i))
                except OSError as e:
                    if i == max_retries - 1:
                        raise OSError(f"Filesystem error after {max_retries} retries: {target_file}. Check disk space and permissions. Original error: {e}")
                    time.sleep(base_delay * (2 ** i))
            return False
        else:
            # Unix: 真正的原子操作
            temp_file.replace(target_file)
            return True

    def rename_symbol_atomic(
        self, old_name: str, new_name: str
    ) -> Tuple[bool, Optional[str], int]:
        """原子性符号重命名 - 跨文件无锁操作"""
        if not self._validate_symbol_name(old_name) or not self._validate_symbol_name(new_name):
            return False, "Invalid symbol name", 0

        # 查找所有引用
        refs = self.search(SearchQuery(old_name, "symbol")).matches
        edits = []

        for ref in refs:
            file_path = ref.get("file")
            if not file_path:
                continue

            full_path = self._resolve_file_path(file_path)
            if not full_path.exists():
                continue

            old_content = full_path.read_text(encoding="utf-8")
            new_content = re.sub(
                r"\b" + re.escape(old_name) + r"\b", new_name, old_content
            )

            if old_content != new_content:
                # 使用统一的hash计算方法
                old_hash = self._hash_content(old_content)
                edits.append(
                    ImmutableEdit(
                        file_path=str(full_path),
                        old_hash=old_hash,
                        new_content=new_content,
                        operation_id=self._get_next_operation_id()
                    )
                )

        if not edits:
            return True, None, 0

        success, error = self.edit_files_atomic(edits)
        return success, error, len(edits)

    def add_import_atomic(
        self, file_path: str, import_statement: str
    ) -> Tuple[bool, Optional[str]]:
        """原子性添加导入 - 智能位置插入，无锁实现"""
        full_path = self._resolve_file_path(file_path)
        if not full_path.exists():
            return False, f"File not found: {file_path}"

        old_content = full_path.read_text(encoding="utf-8")

        # 检查是否已存在 - 使用ripgrep进行精确检测
        if self._check_import_exists_with_ripgrep(str(full_path), import_statement):
            return True, None  # 已存在，无需操作

        # 智能插入位置
        lines = old_content.splitlines()
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                insert_pos = i + 1

        lines.insert(insert_pos, import_statement)
        new_content = "\n".join(lines)

        return self.edit_file_atomic(str(full_path), old_content, new_content)

        # ===== 内部实现 - Linus风格直接数据操作 =====

    def _create_backup(self, file_path: Path) -> Tuple[bool, Optional[str], Optional[str]]:
        """创建备份 - 返回(成功, 备份路径, 错误信息)"""
        try:
            if not file_path.exists():
                return True, None, "File does not exist, no backup needed"

            backup_root = Path.home() / ".code_index_backup"
            backup_root.mkdir(parents=True, exist_ok=True)

            # 使用文件绝对路径的hash作为备份名 - 避免路径冲突
            path_hash = hashlib.sha256(str(file_path.absolute()).encode()).hexdigest()[:8]
            timestamp = int(time.time() * 1000000)
            backup_path = backup_root / f"{file_path.stem}_{path_hash}_{timestamp}.bak"

            shutil.copy2(file_path, backup_path)
            return True, str(backup_path), None

        except PermissionError as e:
            return False, None, f"Permission denied creating backup: {e}"
        except OSError as e:
            return False, None, f"IO error creating backup: {e}"
        except Exception as e:
            return False, None, f"Unexpected error creating backup: {e}"

    def _update_file_in_index(self, file_path: str) -> None:
        """更新文件索引 - 保持数据一致性"""
        try:
            # 强制重新索引文件
            self.force_update_file(file_path)
        except Exception:
            pass  # 索引更新失败不影响文件编辑

    def _resolve_file_path(self, file_path: str) -> Path:
        """解析文件路径 - 统一路径处理"""
        path_obj = Path(file_path)
        if path_obj.is_absolute():
            return path_obj

        base_path = Path(self.base_path) if self.base_path else Path.cwd()
        return base_path / file_path

    def _simple_content_replace(self, current_content: str, old_content: str, new_content: str) -> Optional[str]:
        """Good Taste: 单一清晰的替换语义"""
        # 追加操作 - 明确的API语义
        if not old_content:
            return current_content + new_content

        # 精确替换 - 只有一种行为，用户完全控制匹配
        if old_content in current_content:
            return current_content.replace(old_content, new_content, 1)

        # 未找到 - 明确失败
        return None

    def _validate_symbol_name(self, name: str) -> bool:
        """验证符号名 - 简单正则"""
        return (
            bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name.strip())) if name else False
        )

    def _run_ripgrep_command(self, cmd: List[str], timeout: int = 10) -> Optional[str]:
        """公共的ripgrep命令执行方法 - 统一错误处理和超时"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return None

    def _check_import_exists_with_ripgrep(
        self, file_path: str, import_statement: str
    ) -> bool:
        """使用ripgrep检查导入是否已存在 - 更精确的检测"""
        # 检查ripgrep可用性，fallback到简单检测
        if not shutil.which("rg"):
            # Fallback到原始方法
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                return import_statement in content
            except Exception:
                return False

        # 使用ripgrep进行精确的导入检测
        # 排除注释行的策略：先找到所有匹配，再过滤掉注释行
        escaped_statement = re.escape(import_statement.strip())
        pattern = f"^\\s*{escaped_statement}\\s*$"

        cmd = ["rg", "--line-regexp", "--regexp", pattern, file_path]

        output = self._run_ripgrep_command(cmd)
        if output:
            # 检查找到的行是否是注释行
            for line in output.strip().split("\n"):
                if line and not line.strip().startswith("#"):
                    return True  # 找到非注释行的导入
            return False  # 所有匹配都在注释行中
        else:
            # Fallback到原始方法
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                return import_statement in content
            except Exception:
                return False

    # ===== 文件监控接口 - Linus风格统一入口 =====

    def start_auto_indexing(self, enable: bool = True) -> bool:
        """启动/停止自动文件监控索引 - 统一开关"""
        if enable:
            from .watcher import start_auto_indexing

            return start_auto_indexing(self)
        else:
            from .watcher import stop_auto_indexing

            stop_auto_indexing()
            return True

    def is_auto_indexing_active(self) -> bool:
        """检查自动索引是否活跃"""
        from .watcher import is_auto_indexing_active

        return is_auto_indexing_active()

    def get_watcher_stats(self) -> dict:
        """获取文件监控统计信息"""
        from .watcher import get_watcher_stats

        return get_watcher_stats()

    # SCIP协议方法 - 由integrate_with_code_index添加
    # find_scip_symbol, get_cross_references, export_scip


_global_index: Optional[CodeIndex] = None


def get_index() -> CodeIndex:
    """获取全局索引 - 无锁实现"""
    if _global_index is None:
        raise RuntimeError("Index not initialized")
    return _global_index


def set_project_path(path: str) -> CodeIndex:
    """设置项目路径 - Linus风格简单实现"""
    global _global_index
    _global_index = CodeIndex(base_path=path, files={}, symbols={})

    # Linus原则: 一个函数做完整的事情 - 自动构建索引
    from .builder import IndexBuilder

    builder = IndexBuilder(_global_index)
    builder.build_index(path)  # 传递路径参数

    return _global_index


def index_exists() -> bool:
    """检查索引是否存在 - 无锁实现"""
    return _global_index is not None
