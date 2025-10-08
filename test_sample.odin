package main

import "core:fmt"

main :: proc() {
    fmt.println("Hello, Odin!");
}

Person :: struct {
    name: string,
    age: int,
}

// Function to create a new person
make_person :: proc(name: string, age: int) -> Person {
    return Person{name, age};
}

// Interface example
Drawer :: interface {
    draw :: proc(self: ^Self);
}

Circle :: struct {
    radius: f32,
}

draw_circle :: proc(self: ^Circle) {
    fmt.printf("Drawing circle with radius %f\n", self.radius);
}

// Implement interface for Circle
draw :: proc(self: ^Circle) {
    draw_circle(self);
}