# Verification Discord Bot for THU Student server 

- To be part of the server you have to authenticate yourself as a student of the THU. 
this happens with your student email adress.

- You are more then welcome to contribute and open PR's 
- If you have any concerns please open an issue.


### 📝 TODOs
- Add error messages to:
    > verify_remove: user does not exist
    > 
- Get a new email adress for sending verification email.
- Switch from .json file to actuall Database.
- confirm gives console error when no input.
- move every command to its own file.
- maybe add logging for: 
    > - normal user tries uses admin only command


### Safety

- The user emails are being salted and safed if a json file, so as to prevent double logins, and malicious actors. 
The json file looks something like this. 
```json 
{"353999878579290112": "7f2a9584d8b0ffd7543aea51f6bec53711d6246bd5b63470c393cffea8cf7dd5"}
```


# License

This project is licensed under the MIT License
