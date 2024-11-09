# Verification Discord Bot for THU Student server 

- To be part of the server you have to authenticate yourself as a student of the THU. 
this happens with your student email adress.

- You are more then welcome to contribute and open PR's 
- If you have any concerns please open an issue.


### 📝 TODOs
- confirm gives console error when no input.
- move every command to its own file.
- maybe add logging for: 
    > - normal user tries uses admin only command


### Safety
The user email is hashed with the userid in a database, to prevent the same email,
from connecting twice. ex.

```json 
{"353999878579290112": "7f2a9584d8b0ffd7543aea51f6bec53711d6246bd5b63470c393cffea8cf7dd5"}
```

# License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.
