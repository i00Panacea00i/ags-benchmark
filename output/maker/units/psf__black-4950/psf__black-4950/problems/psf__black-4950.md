# 修复并发模块中 Manager 未正确关闭的问题

在 psf/black 仓库中，src/black/concurrency.py 的异步函数 schedule_formatting() 负责调度格式化任务。当前实现中，参数 write_back 为 WriteBack.DIFF 或 WriteBack.COLOR_DIFF 时，会创建一个 multiprocessing.Manager() 实例，并通过 manager.Lock() 获取锁对象赋值给 lock；但代码从未显式关闭该 Manager。由于 Manager 会启动独立的服务器进程，未调用 shutdown() 或未通过上下文管理器管理其生命周期，会导致资源泄漏。该问题在命令行一次性调用中常被进程立即退出所掩盖，但在将 Black 作为库使用或在长驻进程中重复调用时，会累积泄漏，违反 multiprocessing 最佳实践。

本任务要求修改 src/black/concurrency.py，使上述场景下创建的 Manager 在不再需要时被正确关闭，其服务进程能够终止，且 lock 仍由 manager.Lock() 正常提供并用于并发控制。同时需要在 CHANGES.md 中补充对应的变更说明。相关行为由 tests/test_concurrency_manager_shutdown.py 中的 test_manager_shutdown_called_for_diff 进行验证。

验收标准：
1. 当 write_back 为 WriteBack.DIFF 或 WriteBack.COLOR_DIFF 时，schedule_formatting() 创建的 multiprocessing.Manager() 必须被正确关闭；可观察到其 shutdown() 被调用，或等效的上下文管理器退出逻辑生效，Manager 启动的独立服务进程不再残留。
2. 修复后，tests/test_concurrency_manager_shutdown.py::test_manager_shutdown_called_for_diff 通过。
3. 对 WriteBack.DIFF 与 WriteBack.COLOR_DIFF 的输出行为保持不变，仍能正确生成 diff 或 color diff；lock 的并发控制语义不变。
4. 在长驻进程或作为库重复调用 schedule_formatting() 时，不会因未关闭 Manager 而持续泄漏进程或资源。
5. CHANGES.md 已记录该修复，说明 Manager 生命周期管理得到改进。