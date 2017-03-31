Selfbot
=======

**The current version is untested as I don't really have time to do so. 
YMMV for now.**

This is my personal selfbot, cleaned up a little for public
use. No promises that it's the best bot ever or anything.

It's honestly still a mess, but has less hardcoded stuff. ¯\\\_(ツ)\_/¯

---

* Install Python 3.5 or later
* Set up a Virtualenv if you're using this in production
* `python -m pip install -r requirements.txt`
* Copy `config.yml.example` to `config.yml` and fill it out
* `python -m bot`

Can't find your token? Hit `ctrl+shift+i` in your client, and:

![](https://dl.dropboxusercontent.com/s/xvzffyhee7qrz3t/pycharm64_2017-03-31_23-16-36.png)

---

Need a feature? PR it or suggest it to me. Note that I don't have
much time for this, so I'm likely not going to be going in-depth
with complicated features that I won't get much use from.

I will not be accepting PEP or style-related tickets or PRs. 

Features
========

* Attachments scraper - Saves attachments from every message you can see.
  * Use `/dontsavemebro <id>` to add a user to the blacklist for this if they
    don't want you to save their lewd photos
* `/eval` command for evaluating python code. Supports `await`, `print` and `return` 
  as you'd expect. Can run single lines of code, or you can do the following to run
  a block: ![](https://dl.dropboxusercontent.com/s/9izhq3bpapgcws3/Discord_2017-03-31_23-27-10.png)
    * `self` refers to the current discord.py `Client` for your selfbot
    * `message` refers to the message you just sent containing the command
* `/quote <message id>` command for quoting a message in the current channel using
  an embed. Add a new line and type a message to go with it if you'd like.
* `/repost <message i>` command for quoting a message without an embed or an
  extra message. Only really useful for finding out what another user did in
  their markdown. It will mention the user - be warned.
* `/logs` command which attempts to download every message from the current
  channel and upload it to `gist.github.com`. If it works (or breaks), the message
  you used to type your command will be edited when the task is done with the
  URL to the gist, or any errors that occurred.
