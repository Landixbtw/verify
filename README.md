# Verification Discord Bot for THU Student server 

- To be part of the server you have to authenticate yourself as a student of the THU. 
this happens with your student email adress.

- You are more then welcome to contribute and open PR's 
- If you have any concerns security or otherwise please open an issue. Or contact the moderation team on the discord server via Modmail.


### 📝 TODOs
- confirm gives console error when no input.
- move every command to its own file.
- maybe add logging for: 
    > - normal user tries uses admin only command


### Safety
The user email is hashed with the userid in a database, to prevent the same email,
from connecting twice. ex.

```json 
{"353999878579290112": "5b63bb9ceb264f891bd62606d49685b773e12eb5068a9ef1212612cf826e09ff"}
```

# License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.
