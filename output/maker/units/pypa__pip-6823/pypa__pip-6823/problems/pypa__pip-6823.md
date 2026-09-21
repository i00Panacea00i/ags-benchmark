# Report windows paths in their original case

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
**Environment**

* pip version: 19.2.1
* Python version: 3.7
* OS: Windows

<!-- Feel free to add more information about your environment here -->

**Description**
On Windows; pip reports certain paths after lowercasing them. 

**Expected behavior**
Paths should be reported in their original case.

**How to Reproduce**
`pip install setuptools`

**Output**
`Requirement already satisfied: setuptools in c:\users\my user name\miniconda3\lib\site-packages (41.0.1)`
but the following would be nicer:
`Requirement already satisfied: setuptools in C:\Users\My User Name\miniconda3\lib\site-packages (41.0.1)`

Similar issues:    Admittedly a minor cosmetic point, though.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：a975006fe00a。