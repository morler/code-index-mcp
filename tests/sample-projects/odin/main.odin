package main

import "core:fmt"
import "core:os"

Person :: struct {
	name: string,
	age:  int,
}

main :: proc() {
	person := Person{
		name = "John Doe",
		age  = 30,
	}
	
	fmt.printf("Name: %s, Age: %d\n", person.name, person.age)
}