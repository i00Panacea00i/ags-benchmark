# zsh completion setup fails with 'parse error near elif'

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
When setting up zsh on the back of git for Windows bash shell, zsh throws a parse error when setting up autocomplete.
                                              
  Note: using this in a Python venv, but other aspects of the zsh command line are working.
                                                                                                                                                                                                                           
  The zsh in use is the msys2 release:                                                                                                                     
   
  ## Minimal Reproduction

  
                                                                                                                                                                                                                        
  Enable autocompletion:                                                                                                                                                                                                   
                                                                                                                                                                                                                           
  ```bash
  eval "$(_TUPLE_PARAM_COMPLETE=zsh_source tuple-param)"                                                                                                                                                                   
   ```                                        
  
```bash
Error:                                  

  zsh: parse error near `elif'                                                                                                                                                                                             
```   
                  
  The command should register zsh completion without errors.

  Environment:

  - Python version: 3.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：b8b9ffeb5d01。