<map version="1.0.1">
<!--To view this file, download free mind mapping software FreeMind from http://freemind.sourceforge.net -->
<node BACKGROUND_COLOR="#336699" COLOR="#ffffff" FOLDED="false" TEXT="java.util 集合框架" STYLE="bubble">
  <font NAME="Microsoft YaHei" SIZE="18" BOLD="true"/>
  <edge COLOR="#336699"/>

  <!-- ==================== Collection 体系 ==================== -->
  <node BACKGROUND_COLOR="#2E8B57" COLOR="#ffffff" FOLDED="false" POSITION="right" TEXT="Collection 体系（单列集合）" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#2E8B57"/>

    <!-- List -->
    <node BACKGROUND_COLOR="#3CB371" COLOR="#ffffff" FOLDED="false" TEXT="List（有序 · 可重复 · 有索引）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#3CB371"/>

      <node BACKGROUND_COLOR="#90EE90" COLOR="#333333" FOLDED="false" TEXT="ArrayList" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#90EE90"/>
        <node TEXT="实现：动态数组" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="查询：O(1)  增删尾：O(1)  中间：O(n)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="扩容：1.5 倍" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="线程：不安全" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="推荐：最常用的 List 实现" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>

      <node BACKGROUND_COLOR="#90EE90" COLOR="#333333" FOLDED="false" TEXT="LinkedList" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#90EE90"/>
        <node TEXT="实现：双向链表" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="增删：O(1)  查询：O(n)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="特殊：同时实现 Deque 接口" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="线程：不安全" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>

      <node BACKGROUND_COLOR="#90EE90" COLOR="#333333" FOLDED="false" TEXT="Vector（已过时）" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#90EE90"/>
        <node TEXT="实现：动态数组" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="线程：安全（synchronized）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="扩容：2 倍" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node BACKGROUND_COLOR="#d0f0d0" COLOR="#333333" FOLDED="false" TEXT="Stack（已过时）" STYLE="bubble">
          <font NAME="Microsoft YaHei" SIZE="10"/>
          <node TEXT="继承 Vector，LIFO 栈" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="方法：push / pop / peek" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="推荐替代：ArrayDeque" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        </node>
      </node>
    </node>

    <!-- Set -->
    <node BACKGROUND_COLOR="#20B2AA" COLOR="#ffffff" FOLDED="false" TEXT="Set（无序 · 不重复 · 无索引）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#20B2AA"/>

      <node BACKGROUND_COLOR="#AFEEEE" COLOR="#333333" FOLDED="false" TEXT="HashSet" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#AFEEEE"/>
        <node TEXT="实现：基于 HashMap 的 Key" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="特点：无序，允许一个 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="增删查：O(1)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="原理：hashCode() + equals()" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node BACKGROUND_COLOR="#d0f5f5" COLOR="#333333" FOLDED="false" TEXT="LinkedHashSet" STYLE="bubble">
          <font NAME="Microsoft YaHei" SIZE="10"/>
          <node TEXT="实现：基于 LinkedHashMap 的 Key" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="特点：维护插入顺序" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        </node>
      </node>

      <node BACKGROUND_COLOR="#AFEEEE" COLOR="#333333" FOLDED="false" TEXT="TreeSet" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#AFEEEE"/>
        <node TEXT="实现：基于 TreeMap（红黑树）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="特点：自动排序，不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="增删查：O(log n)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="排序：Comparable 或 Comparator" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
    </node>

    <!-- Queue -->
    <node BACKGROUND_COLOR="#4682B4" COLOR="#ffffff" FOLDED="false" TEXT="Queue（队列 · FIFO）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#4682B4"/>

      <node BACKGROUND_COLOR="#B0C4DE" COLOR="#333333" FOLDED="false" TEXT="PriorityQueue" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#B0C4DE"/>
        <node TEXT="实现：小顶堆（默认）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="特点：按优先级出队，非严格 FIFO" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="增删：O(log n)  查堆顶：O(1)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="限制：不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>

      <node BACKGROUND_COLOR="#B0C4DE" COLOR="#333333" FOLDED="false" TEXT="Deque（双端队列接口）" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <edge COLOR="#B0C4DE"/>
        <node BACKGROUND_COLOR="#d0e8f5" COLOR="#333333" FOLDED="false" TEXT="ArrayDeque" STYLE="bubble">
          <font NAME="Microsoft YaHei" SIZE="10"/>
          <node TEXT="实现：循环数组" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="特点：两端 O(1)，无容量限制" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="推荐：替代 Stack 和 Queue" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
          <node TEXT="限制：不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        </node>
        <node BACKGROUND_COLOR="#d0e8f5" COLOR="#333333" TEXT="LinkedList（同时实现 List+Deque）" STYLE="bubble">
          <font NAME="Microsoft YaHei" SIZE="10"/>
        </node>
      </node>
    </node>
  </node>

  <!-- ==================== Map 体系 ==================== -->
  <node BACKGROUND_COLOR="#8B4513" COLOR="#ffffff" FOLDED="false" POSITION="right" TEXT="Map 体系（双列集合 · Key-Value）" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#8B4513"/>

    <node BACKGROUND_COLOR="#CD853F" COLOR="#ffffff" FOLDED="false" TEXT="HashMap" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#CD853F"/>
      <node TEXT="实现：数组 + 链表 / 红黑树（JDK8+）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="特点：无序，Key/Value 均允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="增删查：O(1)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="初始容量：16，负载因子：0.75" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="链表转红黑树阈值：8，退化：6" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="线程：不安全" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node BACKGROUND_COLOR="#f5deb3" COLOR="#333333" FOLDED="false" TEXT="LinkedHashMap" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <node TEXT="实现：HashMap + 双向链表" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="特点：维护插入顺序（或 LRU 访问顺序）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="用途：实现 LRU 缓存" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
    </node>

    <node BACKGROUND_COLOR="#CD853F" COLOR="#ffffff" FOLDED="false" TEXT="TreeMap" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#CD853F"/>
      <node TEXT="实现：红黑树" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="特点：按 Key 自动排序，Key 不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="增删查：O(log n)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="排序：Comparable 或 Comparator" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#CD853F" COLOR="#ffffff" FOLDED="false" TEXT="Hashtable（已过时）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12" BOLD="true"/>
      <edge COLOR="#CD853F"/>
      <node TEXT="线程：安全（全方法 synchronized）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="限制：Key/Value 均不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="推荐替代：ConcurrentHashMap" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node BACKGROUND_COLOR="#f5deb3" COLOR="#333333" FOLDED="false" TEXT="Properties" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="11"/>
        <node TEXT="继承 Hashtable，Key/Value 均为 String" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="用途：读写 .properties 配置文件" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="方法：load() / store() / getProperty()" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
    </node>

    <node BACKGROUND_COLOR="#CD853F" COLOR="#ffffff" FOLDED="false" TEXT="WeakHashMap" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="12"/>
      <edge COLOR="#CD853F"/>
      <node TEXT="特点：Key 为弱引用，GC 可自动回收" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="用途：缓存场景，防止内存泄漏" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>
  </node>

  <!-- ==================== 并发集合 ==================== -->
  <node BACKGROUND_COLOR="#8B008B" COLOR="#ffffff" FOLDED="false" POSITION="left" TEXT="并发集合（java.util.concurrent）" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#8B008B"/>

    <node BACKGROUND_COLOR="#BA55D3" COLOR="#ffffff" FOLDED="false" TEXT="ConcurrentHashMap" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#BA55D3"/>
      <node TEXT="线程安全的 HashMap 替代品" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="JDK7：分段锁（Segment）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="JDK8：CAS + synchronized（细粒度）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="Key/Value 不允许 null" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#BA55D3" COLOR="#ffffff" FOLDED="false" TEXT="CopyOnWriteArrayList" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#BA55D3"/>
      <node TEXT="线程安全的 ArrayList 替代品" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="写时复制（Copy-On-Write）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="适用：读多写少场景" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#BA55D3" COLOR="#ffffff" FOLDED="false" TEXT="CopyOnWriteArraySet" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#BA55D3"/>
      <node TEXT="线程安全的 Set，基于 CopyOnWriteArrayList" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#BA55D3" COLOR="#ffffff" FOLDED="false" TEXT="ConcurrentLinkedQueue" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#BA55D3"/>
      <node TEXT="线程安全的无界队列，CAS 实现" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#BA55D3" COLOR="#ffffff" FOLDED="false" TEXT="BlockingQueue 接口" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#BA55D3"/>
      <node TEXT="用途：生产者-消费者模式" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node BACKGROUND_COLOR="#dda0dd" COLOR="#333333" FOLDED="false" TEXT="ArrayBlockingQueue" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="10"/>
        <node TEXT="有界阻塞队列，数组实现" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
      <node BACKGROUND_COLOR="#dda0dd" COLOR="#333333" FOLDED="false" TEXT="LinkedBlockingQueue" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="10"/>
        <node TEXT="可选有界阻塞队列，链表实现" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
      <node BACKGROUND_COLOR="#dda0dd" COLOR="#333333" FOLDED="false" TEXT="PriorityBlockingQueue" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="10"/>
        <node TEXT="优先级无界阻塞队列" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
      <node BACKGROUND_COLOR="#dda0dd" COLOR="#333333" FOLDED="false" TEXT="SynchronousQueue" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="10"/>
        <node TEXT="无缓冲，直接传递，用于线程池" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
    </node>
  </node>

  <!-- ==================== 工具类 & 接口 ==================== -->
  <node BACKGROUND_COLOR="#B8860B" COLOR="#ffffff" FOLDED="false" POSITION="left" TEXT="工具类 &amp; 核心接口" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#B8860B"/>

    <node BACKGROUND_COLOR="#DAA520" COLOR="#333333" FOLDED="false" TEXT="Collections（工具类）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#DAA520"/>
      <node TEXT="sort(list)             排序" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="binarySearch(list, key) 二分查找" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="reverse(list)          反转" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="shuffle(list)          随机打乱" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="frequency(c, o)        统计出现次数" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="unmodifiableXxx()      返回只读视图" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="synchronizedXxx()      返回线程安全视图" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="disjoint(c1, c2)       判断是否无交集" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#DAA520" COLOR="#333333" FOLDED="false" TEXT="Arrays（工具类）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#DAA520"/>
      <node TEXT="asList(T...)     数组转固定 List" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="sort(arr)        排序" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="binarySearch()   二分查找" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="copyOf()         复制数组" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="fill()           填充" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="stream()         转换为 Stream" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="equals()         比较数组内容" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#DAA520" COLOR="#333333" FOLDED="false" TEXT="Iterator（迭代器接口）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#DAA520"/>
      <node TEXT="hasNext()  是否还有元素" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="next()     获取下一个元素" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="remove()   删除当前元素（安全删除）" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node BACKGROUND_COLOR="#ffe4b5" COLOR="#333333" FOLDED="false" TEXT="ListIterator（List 专用）" STYLE="bubble">
        <font NAME="Microsoft YaHei" SIZE="10"/>
        <node TEXT="支持双向遍历：hasPrevious() / previous()" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
        <node TEXT="支持修改：set() / add()" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      </node>
    </node>

    <node BACKGROUND_COLOR="#DAA520" COLOR="#333333" FOLDED="false" TEXT="Comparable（自然排序接口）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#DAA520"/>
      <node TEXT="int compareTo(T o)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="由类本身实现，定义自然顺序" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="返回负数：小于；0：等于；正数：大于" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#DAA520" COLOR="#333333" FOLDED="false" TEXT="Comparator（定制排序接口）" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#DAA520"/>
      <node TEXT="int compare(T o1, T o2)" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="外部定义，灵活切换排序规则" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="JDK8+ 支持 Lambda：(a, b) -> a - b" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>
  </node>

  <!-- ==================== 选型指南 ==================== -->
  <node BACKGROUND_COLOR="#DC143C" COLOR="#ffffff" FOLDED="false" POSITION="left" TEXT="选型速查" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#DC143C"/>

    <node BACKGROUND_COLOR="#FA8072" COLOR="#333333" FOLDED="false" TEXT="List 选型" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#FA8072"/>
      <node TEXT="随机访问多         → ArrayList" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="频繁头尾增删       → ArrayDeque" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="频繁中间增删       → LinkedList" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="线程安全           → CopyOnWriteArrayList" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#FA8072" COLOR="#333333" FOLDED="false" TEXT="Set 选型" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#FA8072"/>
      <node TEXT="不关心顺序         → HashSet" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="保持插入顺序       → LinkedHashSet" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="需要自动排序       → TreeSet" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#FA8072" COLOR="#333333" FOLDED="false" TEXT="Map 选型" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#FA8072"/>
      <node TEXT="最通用             → HashMap" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="保持插入顺序/LRU   → LinkedHashMap" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="按 Key 排序        → TreeMap" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="多线程             → ConcurrentHashMap" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="配置文件           → Properties" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#FA8072" COLOR="#333333" FOLDED="false" TEXT="Queue/Stack 选型" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11"/>
      <edge COLOR="#FA8072"/>
      <node TEXT="普通队列/栈        → ArrayDeque" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="优先级队列         → PriorityQueue" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="生产者消费者       → BlockingQueue" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>
  </node>

  <!-- ==================== 学习路线 ==================== -->
  <node BACKGROUND_COLOR="#2F4F4F" COLOR="#ffffff" FOLDED="false" POSITION="right" TEXT="学习路线" STYLE="bubble">
    <font NAME="Microsoft YaHei" SIZE="14" BOLD="true"/>
    <edge COLOR="#2F4F4F"/>

    <node BACKGROUND_COLOR="#708090" COLOR="#ffffff" FOLDED="false" TEXT="第一阶段：基础三件套" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11" BOLD="true"/>
      <edge COLOR="#708090"/>
      <node TEXT="ArrayList   — 最常用 List" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="HashMap     — 最常用 Map" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="HashSet     — 最常用 Set" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="重点：理解 hashCode/equals 契约" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#708090" COLOR="#ffffff" FOLDED="false" TEXT="第二阶段：横向扩展" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11" BOLD="true"/>
      <edge COLOR="#708090"/>
      <node TEXT="ArrayDeque  — 替代 Stack/Queue" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="LinkedHashMap — 实现 LRU 缓存" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="TreeMap/TreeSet — 排序场景" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="PriorityQueue — 优先级调度" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#708090" COLOR="#ffffff" FOLDED="false" TEXT="第三阶段：深入原理" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11" BOLD="true"/>
      <edge COLOR="#708090"/>
      <node TEXT="HashMap 源码 — 扩容/哈希冲突/红黑树" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="ArrayList 源码 — 1.5倍扩容机制" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="fail-fast vs fail-safe 迭代器" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>

    <node BACKGROUND_COLOR="#708090" COLOR="#ffffff" FOLDED="false" TEXT="第四阶段：并发实践" STYLE="bubble">
      <font NAME="Microsoft YaHei" SIZE="11" BOLD="true"/>
      <edge COLOR="#708090"/>
      <node TEXT="ConcurrentHashMap — 多线程键值对" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="CopyOnWriteArrayList — 读多写少" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
      <node TEXT="BlockingQueue — 生产者消费者" STYLE="fork"><font NAME="Microsoft YaHei" SIZE="10"/></node>
    </node>
  </node>

</node>
</map>
