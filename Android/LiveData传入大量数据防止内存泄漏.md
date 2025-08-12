核心要点：LiveData 会“缓存最后一次值”。一旦把超大对象（Bitmap、ByteArray、巨型 List 等）塞进去，在 ViewModel 未销毁前它会一直被持有，从而导致内存占用增大，配合 observeForever 或错误的作用域更会演变成泄漏。建议从“数据设计 + 生命周期 + 事件通道”三方面入手。

一、数据设计：避免把大对象直接放进 LiveData
- 只在 LiveData 里放轻量引用或标识符：
  - 大图/文件：传 Uri、文件路径、ContentProvider 标识，实际加载交给 Glide/Coil 或流式读取。
  - 大列表：传查询条件，由仓库/Room 查询，UI 只观察分页结果。
- 利用 Paging 3 对超大列表分页，避免一次性把全量数据驻留内存。
  ```kotlin
  class UsersViewModel : ViewModel() {
      val pagingFlow = Pager(
          PagingConfig(pageSize = 30, prefetchDistance = 1, enablePlaceholders = false)
      ) { UsersPagingSource(repo) }.flow.cachedIn(viewModelScope)
  }
  ```
- 不要把 Context、View、Drawable 等放进 LiveData 的值里（这些会长链路地持有 Activity/Fragment）。

二、事件通道选择：一次性大数据尽量不用 LiveData
- LiveData/StateFlow 会持有“最新值”。对一次性传递大数据（导出结果、临时大对象），改用 SharedFlow/Channel（replay=0）或回调，不保留历史值，传完即释放。
  ```kotlin
  class ExportViewModel : ViewModel() {
      private val _exportResult = MutableSharedFlow<File>(replay = 0, extraBufferCapacity = 1)
      val exportResult = _exportResult.asSharedFlow()

      suspend fun export() {
          val file = doHeavyExport()
          _exportResult.emit(file) // 不缓存历史，发完即释放引用
      }
  }

  // Fragment
  viewLifecycleOwner.lifecycleScope.launch {
      viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
          viewModel.exportResult.collect { file -> /* 使用文件路径/Uri */ }
      }
  }
  ```
- 如果业务必须用 LiveData，建议“用完即清”，在观察到后尽快置空，缩短大对象被持有的时间：
  ```kotlin
  class VM : ViewModel() {
      val bigData = MutableLiveData<List<LargeItem>?>()
      fun clearBigData() { bigData.value = null }
  }

  // Fragment
  viewModel.bigData.observe(viewLifecycleOwner) { data ->
      if (data != null) {
          render(data)
          viewModel.clearBigData() // 释放引用，便于 GC
      }
  }
  ```

三、生命周期与观察者：杜绝“活得太久”的引用
- 总是用 observe(lifecycleOwner) 而不是 observeForever。后者必须成对 removeObserver，否则极易泄漏。
  ```kotlin
  class VM : ViewModel() {
      val data = MutableLiveData<Any>()
      private val obs = Observer<Any> { /* ... */ }

      fun startObserveForever() { data.observeForever(obs) }
      override fun onCleared() { data.removeObserver(obs) }
  }
  ```
- 不要让单例/Repository 持有 Activity/Fragment/Adapter 的引用；Repository 层如需监听，尽量用 Flow + lifecycleScope + repeatOnLifecycle 由 UI 端收集。
- 合理作用域：
  - 仅在需要共享时才使用 activityViewModels()；共享 ViewModel 会延长数据生命周期。
  - 页面退出时，视情况主动清理大对象缓存；ViewModel.onCleared() 中将大字段置 null、取消协程。
  ```kotlin
  override fun onCleared() {
      bigBuffer = null
      bigLiveData.value = null
      viewModelScope.coroutineContext.cancelChildren()
  }
  ```

四、针对常见大对象的替代策略
- Bitmap/图片：传 Uri/文件，加载交给 Glide/Coil；配置合理的内存/磁盘缓存；必要时使用缩略图、采样率（inSampleSize）。
- 大文件/字节流：以流式方式处理（InputStream、FileDescriptor），避免一次性读入内存；传路径/句柄而非 ByteArray。
- 大列表：Room + PagingSource，或数据库层 LIMIT/OFFSET 分页。
- 不要把大对象放进 SavedStateHandle/NavArgs/Bundle（有大小限制且会放大内存压力）。

五、辅助措施
- distinctUntilChanged/去重，减少把“相同但新实例”的大对象反复塞进 LiveData。
- 工具：接入 LeakCanary 定位是否是 observeForever、单例持有、闭包捕获导致的泄漏；配合 Memory Profiler 看对象保留路径。
- 若需要在 ViewModel 使用 Context，使用 Application Context（AndroidViewModel）而非 Activity。

简要结论
- 原则：LiveData 不要承载大对象；一次性大数据用 SharedFlow/Channel；确实要用则“用完即清”。
- 管住生命周期：避免 observeForever 漏移除，避免把 UI/Context 放进 LiveData 的值里。
- 用分页、磁盘/Uri、流式处理等方式从源头减小内存占用。