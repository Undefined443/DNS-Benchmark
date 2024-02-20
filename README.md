# DNS Benchmark

DNS 速度测试

依赖:

- pyyaml

```sh
pip install pyyaml
```

- kdig

```sh
brew install knot
```

在配置文件 `config.yaml` 中填写你要测试的域名和 DNS 服务器,然后运行:

```sh
./dns_benchmark.py
````
