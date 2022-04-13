import requests
import os


if __name__ == "__main__":
    os.environ['NO_PROXY'] = '172.0.0.1'
    url = "http://localhost:8000/user"
    data = {"username":"test222", "email":"testemail@emial.com", "password":"testpassword", "phoneNumber":6665554444,
            "firstName":"tst", "lastName":"test"}
    sign_up_req = requests.post(url, data=data)
    print("test")
