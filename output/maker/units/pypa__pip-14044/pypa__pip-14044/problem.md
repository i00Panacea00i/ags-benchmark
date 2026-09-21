# pip install sometimes uses the cache when using `pkg @ file:///path` syntax

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

When using `pkg @ file:///path/to/project/dir` syntax in `pip install`, pip sometimes ends up using the cache instead of building the project directory. This behaviour only occurs with `pip install 'pkg @ file:///path/to/project/dir` - it does not occur with `pip install /path/to/project/dir`.

### Expected behavior

Judging by 's response in [the discussion on PyPA Discord]( the expected behaviour should probably be forcing the use of a build from the local dir when one is specified. It does seem like this is what usually happens, considering I've been unable to make a reproduction that doesn't reuse the cache entry that I uploaded from my PC.

### pip version

26.1.2

### Python version

3.10.20

### OS

Debian 13 (docker repro), Ubuntu 22.04 (where the original cache file got generated)

### How to Reproduce

I was unable to reproduce pip generating the cache entry that pip installs instead of the directory specified in the dependency specifier. To still allow for some level of reproduction, I uploaded the faulty cache entry at  and used it in the below reproduction.

The reproduction was performed in a `python:3.10` Docker image (`docker run -it --rm python:3.10 bash`).

```
mkdir /tmp/repro
cd /tmp/repro
export PIP_CACHE_DIR=/tmp/repro/cache
python3.10 -m venv .venv
.venv/bin/pip install -U 'pip==26.1.2'

mkdir -p /tmp/repro/cache/wheels/9e/32/41/213c095f1dfa427bb3df41ef8612b9c7e3d980c3a5f95d27a8/
wget -O /tmp/repro/cache/wheels/9e/32/41/213c095f1dfa427bb3df41ef8612b9c7e3d980c3a5f95d27a8/red_discordbot-3.5.24-py3-none-any.whl 

mkdir -p /home/ubuntu/work/Red-Install-Tests/deps/repos/Red-DiscordBot
wget -O-  | tar --strip-components=1 -C /home/ubuntu/work/Red-Install-Tests/deps/repos/Red-DiscordBot -xzvf -

.venv/bin/pip install -vvv --no-deps 'Red-DiscordBot @ file:///home/ubuntu/work/Red-Install-Tests/deps/repos/Red-DiscordBot'
```

Here's a Docker file to reproduce this for your convenience:

### Output

There's not a lot of logs, really, but

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：10dfb6b90054。