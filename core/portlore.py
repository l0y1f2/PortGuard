# -*- coding: utf-8 -*-
"""常见端口 / 进程的「常识库」——帮你想起这个端口当初是干什么的。"""

WELL_KNOWN_PORTS = {
    20: "FTP 数据", 21: "FTP 控制", 22: "SSH", 23: "Telnet", 25: "SMTP 邮件发送",
    53: "DNS 域名解析", 67: "DHCP", 69: "TFTP", 80: "HTTP 网站", 110: "POP3 收信",
    123: "NTP 时间同步", 135: "Windows RPC", 137: "NetBIOS 名称", 138: "NetBIOS 数据",
    139: "NetBIOS 会话", 143: "IMAP 收信", 161: "SNMP", 389: "LDAP 目录",
    443: "HTTPS 网站", 445: "SMB 文件共享", 465: "SMTPS", 500: "IPSec",
    514: "Syslog", 587: "SMTP 提交", 631: "打印服务", 636: "LDAPS",
    873: "rsync", 993: "IMAPS", 995: "POP3S",
    1080: "SOCKS 代理", 1099: "Java RMI", 1194: "OpenVPN", 1433: "SQL Server",
    1434: "SQL Server Browser", 1521: "Oracle DB", 1723: "PPTP VPN",
    1883: "MQTT", 2049: "NFS", 2181: "ZooKeeper", 2375: "Docker API(不加密)",
    2376: "Docker API(TLS)", 2379: "etcd 客户端", 2380: "etcd 集群",
    3000: "开发服务器(Node/Grafana/React)", 3001: "开发服务器(备用)",
    3306: "MySQL / MariaDB", 3307: "MySQL(第二实例)", 3389: "远程桌面 RDP",
    4200: "Angular 开发服务器", 4369: "Erlang EPMD", 4433: "HTTPS(备用)",
    4444: "Selenium Grid", 4873: "npm 私服 Verdaccio",
    5000: "开发服务器(Flask/.NET)", 5001: "开发服务器(.NET HTTPS)",
    5005: "Java 远程调试", 5044: "Logstash Beats", 5050: "Mesos",
    5060: "SIP 语音", 5173: "Vite 开发服务器", 5174: "Vite(备用)",
    5432: "PostgreSQL", 5433: "PostgreSQL(第二实例)", 5555: "ADB / 常用调试口",
    5601: "Kibana", 5672: "RabbitMQ AMQP", 5900: "VNC 远程桌面",
    5984: "CouchDB", 6006: "TensorBoard", 6080: "noVNC", 6379: "Redis",
    6380: "Redis(第二实例)", 6443: "Kubernetes API", 6666: "常用自定义口",
    7000: "Cassandra / AirPlay", 7001: "WebLogic", 7077: "Spark Master",
    7474: "Neo4j HTTP", 7687: "Neo4j Bolt", 7777: "常用自定义口",
    8000: "开发服务器(Django/Python)", 8001: "开发服务器(备用)",
    8005: "Tomcat 关闭端口", 8008: "HTTP(备用)", 8009: "Tomcat AJP",
    8020: "Hadoop NameNode", 8069: "Odoo", 8080: "HTTP 备用 / Tomcat / 网关",
    8081: "Nexus / HTTP 备用", 8088: "Hadoop YARN / HTTP 备用",
    8090: "Confluence / HTTP 备用", 8096: "Jellyfin", 8161: "ActiveMQ 控制台",
    8443: "HTTPS 备用 / Tomcat SSL", 8500: "Consul", 8501: "Streamlit",
    8600: "Consul DNS", 8761: "Eureka 注册中心", 8848: "Nacos 注册中心",
    8888: "Jupyter / HTTP 备用", 8889: "Jupyter(备用)",
    9000: "SonarQube / PHP-FPM / MinIO", 9001: "MinIO 控制台 / Supervisor",
    9042: "Cassandra CQL", 9090: "Prometheus", 9091: "Prometheus Pushgateway",
    9092: "Kafka", 9093: "Alertmandanger / Kafka", 9100: "Node Exporter",
    9200: "Elasticsearch HTTP", 9300: "Elasticsearch 集群",
    9411: "Zipkin", 9418: "Git 协议", 9527: "常用自定义口(国内项目常见)",
    9876: "RocketMQ NameServer", 10000: "Webmin", 10909: "RocketMQ Broker",
    11211: "Memcached", 15672: "RabbitMQ 管理台", 16379: "Redis 集群总线",
    18080: "HTTP 备用", 19999: "Netdata", 20880: "Dubbo",
    27017: "MongoDB", 27018: "MongoDB(分片)", 28017: "MongoDB 状态页",
    50000: "DB2 / 常用自定义口", 50070: "Hadoop NameNode Web",
}

# 进程名 -> (技术栈标签, 分类)
PROCESS_HINTS = {
    "node.exe": ("Node.js", "dev"),
    "deno.exe": ("Deno", "dev"),
    "bun.exe": ("Bun", "dev"),
    "java.exe": ("Java", "dev"),
    "javaw.exe": ("Java", "dev"),
    "python.exe": ("Python", "dev"),
    "pythonw.exe": ("Python", "dev"),
    "python3.exe": ("Python", "dev"),
    "uvicorn.exe": ("Python Web", "dev"),
    "gunicorn.exe": ("Python Web", "dev"),
    "php.exe": ("PHP", "dev"),
    "php-cgi.exe": ("PHP", "dev"),
    "ruby.exe": ("Ruby", "dev"),
    "dotnet.exe": (".NET", "dev"),
    "w3wp.exe": ("IIS 应用池", "dev"),
    "iisexpress.exe": ("IIS Express", "dev"),
    "nginx.exe": ("Nginx", "dev"),
    "httpd.exe": ("Apache", "dev"),
    "caddy.exe": ("Caddy", "dev"),
    "mysqld.exe": ("MySQL", "db"),
    "mariadbd.exe": ("MariaDB", "db"),
    "postgres.exe": ("PostgreSQL", "db"),
    "mongod.exe": ("MongoDB", "db"),
    "redis-server.exe": ("Redis", "db"),
    "memcached.exe": ("Memcached", "db"),
    "sqlservr.exe": ("SQL Server", "db"),
    "oracle.exe": ("Oracle", "db"),
    "elasticsearch.exe": ("Elasticsearch", "db"),
    "docker.exe": ("Docker", "container"),
    "dockerd.exe": ("Docker", "container"),
    "com.docker.backend.exe": ("Docker Desktop", "container"),
    "vpnkit.exe": ("Docker 网络", "container"),
    "wslservice.exe": ("WSL", "container"),
    "wslhost.exe": ("WSL", "container"),
    "vmmem.exe": ("虚拟机内存", "container"),
    "vmmemwsl.exe": ("WSL 内存", "container"),
    "kubectl.exe": ("Kubernetes", "container"),
    "minikube.exe": ("Kubernetes", "container"),
    "chrome.exe": ("Chrome", "browser"),
    "msedge.exe": ("Edge", "browser"),
    "firefox.exe": ("Firefox", "browser"),
    "brave.exe": ("Brave", "browser"),
    "code.exe": ("VS Code", "tool"),
    "cursor.exe": ("Cursor", "tool"),
    "idea64.exe": ("IntelliJ IDEA", "tool"),
    "pycharm64.exe": ("PyCharm", "tool"),
    "webstorm64.exe": ("WebStorm", "tool"),
    "goland64.exe": ("GoLand", "tool"),
    "devenv.exe": ("Visual Studio", "tool"),
    "ssh.exe": ("SSH", "tool"),
    "git.exe": ("Git", "tool"),
    "frpc.exe": ("frp 内网穿透", "tool"),
    "frps.exe": ("frp 服务端", "tool"),
    "ngrok.exe": ("ngrok 隧道", "tool"),
    "clash.exe": ("代理客户端", "tool"),
    "clash-verge.exe": ("代理客户端", "tool"),
    "v2ray.exe": ("代理客户端", "tool"),
    "xray.exe": ("代理客户端", "tool"),
    "svchost.exe": ("Windows 服务宿主", "system"),
    "system": ("系统内核", "system"),
    "lsass.exe": ("本地安全授权", "system"),
    "services.exe": ("服务控制", "system"),
    "wininit.exe": ("Windows 初始化", "system"),
    "winlogon.exe": ("登录进程", "system"),
    "csrss.exe": ("客户端服务", "system"),
    "smss.exe": ("会话管理", "system"),
    "spoolsv.exe": ("打印服务", "system"),
    "explorer.exe": ("桌面外壳", "system"),
    "searchindexer.exe": ("搜索索引", "system"),
    "msmpeng.exe": ("Defender 杀毒", "system"),
}

# 绝对不允许结束的进程（杀了会蓝屏 / 强制重启）
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "lsaiso.exe", "ntoskrnl.exe",
}

# 允许结束但要重点警告的进程
RISKY_PROCESSES = {
    "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe",
    "taskhostw.exe", "sihost.exe", "ctfmon.exe", "audiodg.exe",
    "msmpeng.exe", "spoolsv.exe", "wudfhost.exe", "conhost.exe",
}


def describe_port(port: int) -> str:
    if port in WELL_KNOWN_PORTS:
        return WELL_KNOWN_PORTS[port]
    if 49152 <= port <= 65535:
        return "系统动态分配（临时端口）"
    if port < 1024:
        return "系统保留端口段"
    return ""


def describe_process(name: str):
    """返回 (技术栈标签, 分类)"""
    if not name:
        return ("", "other")
    return PROCESS_HINTS.get(name.lower(), ("", "other"))


def kill_risk(name: str) -> str:
    """protected | risky | normal"""
    n = (name or "").lower()
    if n in PROTECTED_PROCESSES:
        return "protected"
    if n in RISKY_PROCESSES:
        return "risky"
    return "normal"
