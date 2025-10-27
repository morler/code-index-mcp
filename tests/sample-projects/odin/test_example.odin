package main

import "core:fmt"

Person :: struct {
	name: string,
	age:  int,
}

main :: proc() {
	person := Person{
		name = "Test User",
		age  = 25,
	}
	
	fmt.printf("Hello from Odin! %s is %d years old\n", person.name, person.age)
}