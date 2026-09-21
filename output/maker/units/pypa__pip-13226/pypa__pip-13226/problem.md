# [UX] Constraint file lookup error message is misleading (a troubleshooting adventure)

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

So I was helping out  diagnose an issue over at  where he's working on building wheels for `codecov-cli` and release automation.

He asked me to help understand an error that was happening during smoke-testing. And the error was ambiguous enough to confuse us both.

Initially, I was presented with
```console
$ pip install codecov_cli-10.1.0-cp311-cp311-macosx_11_0_arm64.whl
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'
```
and a *guess* that pip tries to find a `'requirements.txt'` file within said wheel, and it's not there.

I *knew* that it was impossible, but couldn't understand where it was coming from. And I couldn't reproduce locally. I assumed all sorts of things then (bugs in pip, messed up CPython install/build, somehow broken env in general).

At some point I suggested `--no-deps` because the only place that I expected possibly dealing with requirements installs would be ephemeral build envs. And since the requested install was a wheel, I thought it'd be coming from some dependency that needed to be built from sdist. But that didn't help.

Eventually, I asked for `-vvvvv` and got a traceback pointing to 

But I still couldn't get where the requirement file assumption was coming from. It was driving me crazy. The error said “*requirements* file”.

I inspected the wheel for having acceptable metadata. In a disbelief, I gave in to what Tom was implying at the beginning, and asked him to install some other known-good wheel. *“Could it really be coming from a malformed wheel?”* — I thought to myself, — *“Nooo… It can't be true. I just can't!”*
Tom reported that a different wheel produced the same error, and I restored my faith in at least partially understanding what was going on.

Now what? At this point, I've finally pasted the error into the pip tracker. There wasn't an issue calling out this ambiguity, but I've seen enough hints to make an educated guess.

Together with some other context, 

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：08f7a9b71434。