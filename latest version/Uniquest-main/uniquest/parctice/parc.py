# temp=float(input("Enter the temperature in fahrenhiet to convert it to Celcius: "))
# print((temp-32) / 1.8)
# user = input("Enter a number here: ")
# if user== 0:
#  print("The number is zero")
# else:
#     print("The number is not zero")


# robot briesta
# coffee= 2
# water= 1

# name=input(" what is your name?  " )
# print("Hello " + name + " welcome to our coffee shop")
# menu=input("Here is our menu: \n 1. Coffee \n 2. Tea \n 3. Juice \n 4. Water \n Please select a drink from the menu: ")
# if menu == coffee and tea and juice and water :
#     print("You have selected " + menu + " as your drink. Thank you for your order!")
# print("Your " + menu + " will be ready in 5 minutes. Enjoy your drink!")

# else:
#     print("Not available or wronge spelling")


name = input("What is your name? ")
print("Hi " + name + ", i am your personel AI assistant")
question = input("We have some default questions:\n"
                 "1. What is AI?\n"
                 "2. What is PYAI?\n"
                 "3. What is Python?\n"
                 "4. What is HTML?\n"
                 "5. What is CSS?\n"
                 "6. What is JavaScript?\n"
                 "7. What is cybersecurity?\n"
                 "8. What is a firewall?\n"
                 "9. What is an IP address?\n"
                 "10. What is a VPN?\n"
                 "11. What is Linux?\n"
                 "12. What is Windows?\n"
                 "13. What is RAM?\n"
                 "14. What is an SSD?\n"
                 "15. What is a database?\n"
                 "16. What can you do?\n"
                 "17. Can you write code?\n"
                 "18. Can you solve math problems?\n"
                 "19. Who created you?\n"
                 "20. What model are you?\n"
                 "Please select a question from the list: ")

if question == "1":
    print("AI is technology that enables computers to perform tasks that normally require human intelligence.")

elif question == "2":
    print("PYAI is a Python-based AI framework designed for easy development and deployment of machine learning models.")

elif question == "3":
    print("Python is a popular high-level programming language known for its simplicity and versatility.")

elif question == "4":
    print("HTML is the standard markup language used to structure web pages.")

elif question == "5":
    print("CSS is used to style and design HTML webpages.")

elif question == "6":
    print("JavaScript is a programming language commonly used to make websites interactive.")

elif question == "7":
    print("Cybersecurity is the practice of protecting computers, networks, applications, and data from attacks.")

elif question == "8":
    print("A firewall monitors and controls network traffic based on security rules.")

elif question == "9":
    print("An IP address identifies a device on a network and allows it to communicate with other devices.")

elif question == "10":
    print("A VPN creates an encrypted connection between your device and a VPN server.")

elif question == "11":
    print("Linux is an open-source operating system kernel used in many operating systems and servers.")

elif question == "12":
    print("Windows is a family of operating systems developed by Microsoft.")

elif question == "13":
    print("RAM is temporary memory used by a computer to store data and programs currently in use.")

elif question == "14":
    print("An SSD is a storage device that uses flash memory and is generally faster than a traditional hard drive.")

elif question == "15":
    print("A database is an organized collection of data that can be stored, searched, and managed.")

elif question == "16":
    print("I can answer questions, explain concepts, write code, debug code, summarize information, and help with many other tasks.")

elif question == "17":
    print("Yes, I can generate, explain, debug, and improve code in many programming languages.")

elif question == "18":
    print("Yes, I can help solve mathematical problems and explain the steps.")

elif question == "19":
    print("I was created by Hassan Kazmi.")

elif question == "20":
    print("I am PYAI 1.2.2, a Python-based AI model designed to assist with various tasks.")

else:
    print("Invalid selection. Please select a number from 1 to 20.")