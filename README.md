# DNS Benchmark

DNS 速度测试

依赖:

- `pyyaml`

```sh
pip install pyyaml
```

- `kdig`

```sh
brew install knot
```

在配置文件 `config.yaml` 中填写你要测试的域名和 DNS 服务器,然后运行:

```sh
python dns_benchmark.py
````

## 部分公共 DNS 提供商

[阿里云 DNS](https://www.alidns.com/)

[腾讯 DNSPod](https://www.dnspod.cn/products/publicdns)

[Google DNS](https://developers.google.com/speed/public-dns/docs/using?hl=zh-cn)