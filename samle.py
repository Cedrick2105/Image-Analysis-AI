class Bird:
    def __init__(self,name,age,food):
        self.name=name
        self.age=age
        self.food=food
    def eat(self):
        print(f"The {self.name} with {self.age} years old eat {self.food}")
class hawk(Bird):
    pass
class chicken(Bird):
    pass
a = hawk("hawk",5,"rice")
print(a.eat())
b= chicken("chicken",6,"beans")
print(b.eat())   
        
