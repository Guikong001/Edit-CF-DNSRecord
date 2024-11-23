# Edit-CF-DNSRecord-PY
A PY Script that used for cloudflare dns record editing. shell version and web version.
由于中国大陆时常出现Cloudflare dashboard访问较慢或无法打开的问题，使用API管理DNS记录会更加便利。
该脚本Shell版本，支持增加、修改、删除DNS记录，以及DDNS动态解析。
该脚本的Web版本，可以通过网页的形式访问并进行界面操作。


## Usage

### Shell version
下载并保存Shell_version.py到本地计算机，首先安装脚本需要的python包:

        pip install threading tldextract
随后直接在本地运行

        python Shell_version.py

根据指示输入内容即可完成更改。

### Web version
下载并保存Web_version.py到本地计算机，首先安装脚本需要的python包:

        pip install flask tldextract

随后直接本地运行即可:

        python Web_version.py

此时，将会在10081端口开启一个http监听，使用http://ip:10081即可访问使用。可以使用nginx设置反向代理，使用https访问。
也可以使用screen命令创建一个虚拟终端，将脚本长时间运行在虚拟终端中。

Web版本Demo：[点击访问](https://cf-dns-edit.fanxuepai.cn/)
