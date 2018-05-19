This project is based on the Python final assignment of ICS0015. The purpose was to gain insight what really goes into creating a chat application from scratch with fairly basic functionalities, such as user login and registration, channels and permissions.


The biggest challenge was to get all the intrecate pieces moving smoothly. For example, when the client sends certain data it will also expect certain feedback back.


The 'technologies' used:
  * Threading
  * Sockets
  * SQLite

  
How to test it:
  1.1. Start `Server.py` and `Client.py`
  1.2. Check the server's console. It should say something like `Starting server on 'localhost:8888'`
  1.3. In client, type in `!connect localhost 8888` 
  1.4. You will prompted to log in/register. Log in with root account `!login root M83Kj5QGxWCh2YMG` (that's the default root password)
  
  2.1. You are now logged in
  2.2. Type a few lines in chat
  2.3. Check the available commands with `!help`
  3.4. Test out some of the commands (e.g `!channels` and `!channel admin`). Please note that the root user has full access and some commands can be very destructive
  
  3.1. Open a new client without closing the first one
  3.2. Connect to the same server but this time create a new user with `!register testuser testpassword`
  3.3. Notice the chat history from the first account displayed
  3.4. Type a few lines and see how it's displayed on the other client
  3.5. Attempt to use different commands and see the permission difference between the accounts

  
Few additional notes:
  * There is no GUI as this was not the main focus of this project
  * Channels can have minimum permission requirements. If a user's rank is lower than specified for the channel, the user won't see the channel under the `!channels` command and won't be able to join
  * Channels can have slots assigned to them. For example, a channel with 5 slots can't have more than 5 members. An exception to this is the `join_full` permission, which grants the user the ability to bypass the slot limit.
  * Only the root account can be used to create and remove accounts/channels/permissions