
### Asterisk fastapi 1.1.0

Source code [Github](https://github.com/shurshilov/odoo)


<img src="static/images/fastapi_logo.png" alt="drawing" width="200"/>
<img src="static/images/asterisk_logo.jpeg" alt="drawing" width="200"/>


## What is this program for??
Create web server on the same server as asterix.
This server can:
  1. Provide asterisk calls history by http endpoint like start_datetime and end_datetime (mysql,postgresql,sqlite,csv)
  2. Provide webhooks for asterisk. Allows you to send request to your site, for example, an incoming call that was answered or a missed call. Next, your server saves this to the database and notifies clients (browsers) through any mechanism (websockets, longpolling) that a call has arrived and, for example, by calling a pop-up window and creating a lead or opening a partner's card
  3. Also provide recordngs although they are available in asterix ari, just to address the same address. (essentially a duplication)
  4. Endpoint numbers list
  4. Endpoint checkup ( getting the status of the service)

## How configure Asterisk?

1. Enable the Asterisk HTTP service in /etc/asterisk/http.conf: 
```bash
[general]
enabled = yes
bindaddr = 0.0.0.0
bindport = 8088
```
2. Configure an ARI user in /etc/asterisk/ari.conf:
```bash
[general]
enabled = yes
pretty = yes
allowed_origins = localhost:8088,http://ari.asterisk.org

[asterisk-supersecret]
type = user
read_only = no
password = $6$nqvAB8Bvs1dJ4V$8zCUygFXuXXp8EU3t2M8i.N8iCsY4WRchxe2AYgGOzHAQrmjIPif3DYrvdj5U2CilLLMChtmFyvFa3XHSxBlB/
password_format = crypt
```

## How configure app?

By default, the environment data is read from the **.env** file.
Perhaps the .env.sample file as an example will help you (just rename that).
Please set your credentials to it file before work.

## How start app?

### 1 Variant. Start on host.

On your asterist server. Setup python enviroment. 
Python version 3.11.0 or more.
A best practice among Python developers is to use a project-specific virtual environment. Once you activate that environment, any packages you then install are isolated from other environments, including the global interpreter environment, reducing many complications that can arise from conflicting package versions. You can create non-global environments in VS Code using Venv or Anaconda

```bash
  python -m venv .venv
  python -m pip install -r requirements.txt
```
Start from root folder backend web server (ASGI) as service
```bash
uvicorn main:app --host 127.0.0.1 --port 8082 --log-level debug
```
or
```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8082 --log-level debug --workers 2
```

### 2 Variant. Start on docker.

On your asterist server. Setup docker enviroment.

Start from root folder backend web server (ASGI) as docker service
```bash
  docker-compose -f docker-compose.backend.yml up
```


