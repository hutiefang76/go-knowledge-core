# Go 多线程知识点

> **作者**: frank.hutiefang
> **知乎**: @大大大大大芳
> **微信**: hutiefang
> **版本**: v1.3
> **更新时间**: 2026-01-27

---

## 第一部分：操作系统的多线程知识点

### 1.1 进程 vs 线程

#### 进程（Process）
- 操作系统资源分配的基本单位
- 拥有独立的内存空间（32位系统4GB，64位系统可达128TB+）
- 进程间通信需要IPC（管道、消息队列、共享内存等）
- 创建和切换开销较大（微秒至毫秒级）
- 进程内存占用取决于程序本身，无固定范围

#### 线程（Thread）
- CPU调度的基本单位
- 共享进程的内存空间
- 线程间通信通过共享内存
- 创建和切换开销小（微秒级）
- 线程栈大小通常为1MB-8MB（可配置），最大线程数受限于内存和ulimit配置

#### 协程（Coroutine）
- 用户态线程，由语言运行时调度
- 内存占用极小（KB级别）
- 上下文切换在用户态完成，不涉及系统调用（M：N 复用线程）
- 可创建数量极大（百万级）
- 多种语言实现：Go的goroutine、Java虚拟线程、Kotlin协程、Python asyncio

### 1.2 并行 vs 并发

#### 并行（Parallelism）
- 多个CPU核心同时执行任务
- 真正的同时执行
- 需要多核硬件支持
- 典型应用：科学计算、大数据处理（MapReduce、Spark）

#### 并发（Concurrency）
- 单个CPU核心通过时间分片模拟同时执行
- 逻辑上的同时，物理上的交替
- 减少CPU空闲时间，提高资源利用率
- 典型应用：Web服务器、GUI应用

### 1.3 CPU调度机制

#### 时间分片（Time Slicing）
- CPU时间被划分为小的时间片（Linux通常1-10ms，Windows约15-30ms）
- 每个线程运行一个时间片后切换到下一个
- 通过时钟中断触发上下文切换

#### 上下文切换（Context Switch）
- 保存当前线程的CPU状态（寄存器、PC指针等）
- 恢复下一个线程的CPU状态
- 开销：内核态切换需要1-10μs，用户态切换约100-500ns（视硬件而定）

#### 调度算法
- FIFO（先来先服务）：简单但可能导致长任务阻塞短任务
- Round Robin（轮转）：公平但上下文切换频繁
- Priority Scheduling（优先级）：重要任务优先，但可能导致低优先级任务饥饿
- Work Stealing（工作窃取）：空闲线程从忙碌线程窃取任务，Go的GMP（Goroutine，Machine（M），Processor（P））模型采用此算法

### 1.4 多线程问题

#### 竞态条件（Race Condition）
- 多个线程同时访问共享资源，且至少有一个写操作
- 结果依赖于线程执行顺序
- 例子：`counter++` 操作不是原子的

#### 死锁（Deadlock）
- 两个或多个线程互相等待对方释放资源
- 产生条件：
  - 互斥条件：资源不能共享
  - 不可剥夺条件：资源只能由持有者释放
  - 请求与保持条件：持有资源同时请求新资源
  - 循环等待条件：进程间形成循环等待链

#### 活锁（Livelock）
- 线程不断改变状态，但无法取得进展
- 例子：两个线程互相礼让资源

#### 饥饿（Starvation）
- 某个线程长期无法获得所需资源
- 原因：优先级调度、资源分配不公平

## 第二部分：Go语言基本的多线程使用

### 2.1 Goroutine：Go的并发基石

#### 特性
- 轻量级协程，由Go运行时调度
- 初始栈大小仅2KB，可动态增长
- 创建成本极低，可轻松创建百万级goroutine

#### 通过`go`关键字启动
```go
// 基本用法
go func() {
    fmt.Println("这是一个goroutine")
}()

// 带参数
go func(id int) {
    fmt.Printf("Goroutine %d\n", id)
}(1)
```

#### GMP调度模型
- G (Goroutine)：应用级协程
- M (Machine)：OS线程
- P (Processor)：逻辑处理器，包含runqueue
- 工作窃取：空闲P从其他P的runqueue中窃取任务
  当通过go关键字创建一个新的Goroutine时，该Goroutine会被放入到某个P的队列中等待执行
- 
### 2.2 Channel：goroutine通信管道

#### 核心概念
- CSP（Communicating Sequential Processes）模型的核心
- "不要通过共享内存来通信，而应该通过通信来共享内存"
- 类型安全，编译时检查

####  Channel的三组特性



##### 1. 同步 vs 异步（通信模式）



**概念**

| 模式 | 比喻 | 场景 |
|------|------|------|
| **同步** | 柜台结账：顾客站着等，扣完款才能走 | 扣款必须确认成功 |
| **异步** | 取号等餐：拿号就走，好了通知你 | 发短信、记日志 |

**决策**：下一步依赖这一步结果 → 同步；否则 → 异步
**tips**
> - 无缓冲 → **必然同步**
> - 有缓冲 → **条件异步**（未满时异步，满了就变同步）
> - 
##### 2. 无缓冲 vs 有缓冲（实现方式）

**电商隐喻**

| 类型           | 比喻 | 用途 |
|--------------|------|------|
| **无缓冲（低时延）** | 一对一客服：必须等接起才能说话 | 支付回调（必须确认收到） |
| **小缓冲（综合）**  | 银行叫号机：最多10人等，第11个排队 | 普通订单队列 |
| **大缓冲（高吞吐）** | 双11预售：先收1万单，慢慢处理 | 秒杀（需配合限流） |

**无缓冲**：高并发慢
**大缓冲的坑**：延迟高、问题被隐藏、关机时数据丢失风险
高并发 !=低时延 !=高吞吐


**决策**：不确定 → **先用无缓冲**；生产快消费慢 → 小缓冲；秒杀 → 大缓冲+限流

```go
ch1 := make(chan int)      // 无缓冲，必然同步
ch2 := make(chan int, 10)  // 有缓冲，条件异步

ch2 <- 1  // 异步（未满）
ch2 <- 2  // 异步（未满）
// ... 放满后
ch2 <- 11 // 阻塞！满了，变成同步
```

##### 3. 双向 vs 单向（权限控制）

**电商隐喻**

| 类型 | 比喻 |
|------|------|
| **双向** | 客服对讲机：能说能听，人多容易乱 |
| **只发送** | 订单投递口：前台只管扔进去 |
| **只接收** | 仓库取单窗口：仓库只管取出来 |

**决策**：创建时用双向，传参时限制权限（编译器帮你检查）

```go
// 创建：永远双向
orderQueue := make(chan Order, 100)

// 使用：传参时限制权限（编译器自动转换）
func producer(ch chan<- Order, order Order) { ch <- order }  // 只能发
func consumer(ch <-chan Order) { order := <-ch; _ = order }  // 只能收

go producer(orderQueue, Order{ID: 1})  // 自动转成只发送
go consumer(orderQueue)                 // 自动转成只接收
```

##### 实用矩阵：缓冲 × 方向（共9种组合）

| | 双向(内部用) | 只发送(生产者) | 只接收(消费者) |
|---|---|---|---|
| **无缓冲** | goroutine协调 | 信号发送 | 信号等待 |
| **小缓冲** | 事件队列 | 日志写入 | 流量处理 |
| **大缓冲** | 批处理 | 高吞吐生产 | 批量消费 |

### 2.3 同步原语

> **核心认知**：Channel用于goroutine间传递数据，同步原语用于协调goroutine的执行顺序和保护共享数据

#### sync.WaitGroup —— 等所有人到齐

**电商隐喻：团购凑单**
- 发起团购，需要凑齐5人才能发货
- 每有一人下单，计数+1；每有一人付款完成，计数-1
- 主线程等待（Wait），直到计数归零才发货

| 方法 | 比喻 | 作用 |
|------|------|------|
| `Add(n)` | 团购需要n人 | 增加等待计数 |
| `Done()` | 又有1人付款完成 | 计数减1 |
| `Wait()` | 等凑齐了再发货 | 阻塞直到计数归零 |

```go
var wg sync.WaitGroup
wg.Add(3) // 需要等3个任务

for i := 0; i < 3; i++ {
    go func(id int) {
        defer wg.Done() // 完成一个，计数-1
        处理订单(id)
    }(i)
}

wg.Wait() // 等3个都完成，再继续
fmt.Println("所有订单处理完毕")
```

#### sync.Mutex —— 互斥锁

**电商隐喻：试衣间**
- 试衣间一次只能进一个人
- 进去要锁门（Lock），出来要开门（Unlock）
- 其他人在门口排队等

| 操作 | 比喻 | 作用 |
|------|------|------|
| `Lock()` | 进试衣间，锁门 | 获取锁，其他人等待 |
| `Unlock()` | 出来，开门 | 释放锁，下一个进入 |

**什么时候用？** 多个goroutine要修改同一个变量

```go
var mu sync.Mutex
var 库存 = 100

func 扣库存() {
    mu.Lock()         // 锁门
    defer mu.Unlock() // 确保出来时开门
    库存--            // 安全修改
}

// 100个goroutine同时扣库存，不会超卖
```

#### sync.RWMutex —— 读写锁

**电商隐喻：商品详情页**
- 看商品详情（读）：可以很多人同时看
- 改商品价格（写）：必须清场，改完才能继续看
- 读多写少时，比Mutex效率高

| 操作 | 比喻 | 作用 |
|------|------|------|
| `RLock()` | 进店看商品 | 获取读锁，可多人同时 |
| `RUnlock()` | 看完离开 | 释放读锁 |
| `Lock()` | 清场改价格 | 获取写锁，独占 |
| `Unlock()` | 改完开门 | 释放写锁 |

```go
var rwmu sync.RWMutex
var 商品价格 = 99.00

func 查看价格() float64 {
    rwmu.RLock()         // 读锁，可多人同时读
    defer rwmu.RUnlock()
    return 商品价格
}

func 修改价格(新价格 float64) {
    rwmu.Lock()          // 写锁，独占
    defer rwmu.Unlock()
    商品价格 = 新价格
}
```

**决策**：读多写少 → RWMutex；写操作频繁 → Mutex

#### context —— 超时与取消

**电商隐喻：外卖配送**
- 下单时设置"30分钟超时"
- 骑手（goroutine）随时检查是否超时或被取消
- 超时了就不送了，及时止损

| 函数 | 比喻 | 作用 |
|------|------|------|
| `WithTimeout` | 设置配送时限 | 超时自动取消 |
| `WithCancel` | 用户可随时取消订单 | 手动取消 |
| `ctx.Done()` | 骑手检查订单状态 | 收到取消信号 |
| `cancel()` | 用户点"取消订单" | 发出取消信号 |

```go
// 设置2秒超时
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel() // 别忘了释放资源

select {
case 结果 := <-处理订单():
    fmt.Println("订单完成:", 结果)
case <-ctx.Done():
    fmt.Println("超时了:", ctx.Err()) // 及时止损
}
```

**什么时候用？**
- 调用外部API，防止卡死 → WithTimeout
- 用户取消操作，通知所有goroutine停止 → WithCancel
- 请求链路追踪，传递请求ID → WithValue

#### 同步原语选择矩阵

| 场景 | 选择 | 理由 |
|------|------|------|
| 等多个goroutine完成 | WaitGroup | 团购凑单 |
| 保护共享变量（写多） | Mutex | 试衣间 |
| 保护共享变量（读多写少） | RWMutex | 商品详情页 |
| 超时控制 | context.WithTimeout | 外卖配送时限 |
| 手动取消 | context.WithCancel | 用户取消订单 |
| goroutine间传数据 | Channel | 不是同步原语，但更推荐 |

### 2.4 select语句：多路复用
- 同时监听多个channel操作
- 非阻塞通信基础
- 实现超时、重试等模式

```go
select {
case data := <-ch1:
    fmt.Println("Received from ch1:", data)
case <-time.After(1 * time.Second):
    fmt.Println("Timeout")
case ch2 <- 42:
    fmt.Println("Sent to ch2")
default:
    fmt.Println("No communication ready")
}
```

## 第三部分：多线程问题和线程不安全

### 3.1 线程不安全的三大特性

#### 3.1.1 可见性（Visibility）
- 问题：一个goroutine修改共享变量后，其他goroutine可能看不到最新值，因为：
  - CPU缓存不一致（MESI协议）
  - 编译器优化重排序
  - 处理器指令重排序
- Go解决方案：
  - sync.Mutex：锁操作包含内存屏障，保证可见性
  - sync/atomic：原子操作，包含内存屏障
  - Channel：通过channel通信天然保证可见性
  - sync.Once：保证初始化操作只执行一次
- (代码块)
  - (代码块)
```go
var (
    mu      sync.Mutex
    flag    bool
    counter int
)

// 通过锁保证可见性
func writer() {
    mu.Lock()
    counter = 10
    flag = true
    mu.Unlock()
}

func reader() {
    mu.Lock()
    defer mu.Unlock()
    if flag {
        fmt.Println(counter) // 保证看到最新值
    }
}
```

#### 3.1.2 原子性（Atomicity）
- 问题：复合操作（如`counter++`）被中断，导致数据不一致：
  - 读取counter值到CPU寄存器
  - 寄存器值+1
  - 写回counter
- Go解决方案：
  - sync.Mutex：锁保护整个操作
  - sync/atomic：原子操作（AddInt32, CompareAndSwap等）
  - sync.Map：并发安全的map
  - (代码块)
    - (代码块)
```go
var counter int32

// 原子操作
func atomicIncrement() {
    atomic.AddInt32(&counter, 1)
}

// CAS操作
func compareAndSwap(old, new int32) bool {
    return atomic.CompareAndSwapInt32(&counter, old, new)
}
```

#### 3.1.3 有序性（Orderliness）

> **happens-before（发生在...之前）**：不是真正的时间顺序，而是"保证能看到"的顺序。如果A happens-before B，那么A的结果对B可见。

**电商隐喻：签收确认**
- 仓库发货（写数据） happens-before 用户签收（读数据）
- 只有确认发货了，用户才能签收到正确的商品

- 问题：编译器和处理器为了优化性能，可能重排序指令，导致程序行为不符合预期。
  - Go内存模型保证的happens-before关系：
    - 单个goroutine内，按程序顺序happens-before
    - 无缓冲channel：发送完成 happens-before 接收完成
    - 有缓冲channel：第k次接收完成 happens-before 第k+C次发送完成（C为缓冲大小）
    - channel关闭：close happens-before 接收方收到零值
    - 锁操作：解锁happens-before后续加锁
    - sync.Once.Do：初始化happens-before后续调用
- Go解决方案：
  - Channel：通过通信保证顺序
  - sync.WaitGroup：等待特定操作完成后再继续
  - sync.Once：保证初始化顺序

```go
// 错误示例：没有happens-before保证（存在数据竞争）
var data = 0
var ready = false

go func() {
    data = 42      // 写数据
    ready = true   // 可能被重排序到data=42之前！
}()

// 问题1：主goroutine可能在子goroutine启动前就检查ready
// 问题2：即使用循环等待，也可能因编译器优化永远看不到ready=true
// 问题3：即使看到ready=true，data也可能因重排序仍为0
for !ready {
    // 忙等待（本身也有问题，仅作演示）
}
fmt.Println(data) // 可能打印0！

// 正确做法：用channel建立happens-before关系
done := make(chan bool)

go func() {
    data = 42
    done <- true  // 发送 happens-before 接收
}()

<-done           // 接收
fmt.Println(data) // 保证打印42
```

### 3.2 隔离性（Isolation）
- 问题：不同goroutine之间数据相互干扰，特别是局部状态。

#### Go解决方案：
- Goroutine局部变量：每个goroutine有自己的栈空间
- context.Value：请求范围数据隔离
- sync.Pool：对象池，减少GC压力，但注意隔离性
- (代码块)
  - (代码块)
```go
// context.Value隔离
type keyType string
const requestIDKey keyType = "request_id"

func handleRequest(ctx context.Context) {
    requestID := ctx.Value(requestIDKey).(string)
    // 每个请求有自己的requestID
}
```

### 3.3 不可变性（Immutability）
- 问题：可变数据导致并发复杂性。

#### Go解决方案：
- 字符串不可变：Go字符串天生不可变
- 不可变数据结构：创建新对象而不是修改原对象
- sync/atomic.Value：原子地存储和加载不可变对象
- (代码块)
  - (代码块)
```go
// 不可变配置
type Config struct {
    host    string
    port    int
    timeout time.Duration
}

// 创建新配置，而不是修改旧配置
func (c *Config) WithHost(newHost string) *Config {
    return &Config{
        host:    newHost,
        port:    c.port,
        timeout: c.timeout,
    }
}
```

### 3.4 Go标准库容器的线程安全性

#### 默认不安全的容器：
- map：非并发安全，需要sync.Mutex或sync.RWMutex保护
- slice：非并发安全，需要锁保护
- container/list.List：非并发安全

#### 并发安全的容器：
- sync.Map：并发安全的map，适用于读多写少场景
- sync.Pool：对象池，减少GC压力（注意：获取的对象状态不确定，需使用前重置）
- channel：并发安全的通信管道
- atomic.Value：原子地存储和加载任意类型
- (代码块)
  - (代码块)
```go
// sync.Map 使用
var safeMap sync.Map

// 存储
safeMap.Store("key", "value")

// 读取
if val, ok := safeMap.Load("key"); ok {
    fmt.Println(val)
}

// 删除
safeMap.Delete("key")
```

#### sync.Map vs 普通map+锁：
- sync.Map：适用于读多写少、键值不频繁变化的场景
- map+sync.RWMutex：适用于写操作较多、需要复杂操作的场景

## 第四部分：Go语言并发最佳实践

### 4.1 设计原则
- 优先使用channel：遵循CSP原则，避免共享内存
- 最小化共享状态：只在必要时共享数据
- 使用context传递取消信号：优雅关闭goroutine
- 避免goroutine泄漏：确保每个goroutine都有退出条件
- 不要过度优化：先保证正确性，再考虑性能

### 4.2.1 锁优化

#### 避免不必要的锁
- (代码块)
  - (代码块)
```go
// 坏：整个函数加锁
func badIncrement() {
    mu.Lock()
    defer mu.Unlock()
    // 1. 读取配置（不需要锁）
    config := readConfig()
    // 2. 计算（不需要锁）
    result := compute(config)
    // 3. 更新共享状态（需要锁）
    sharedData = result
}

// 好：只锁需要的部分
func goodIncrement() {
    config := readConfig()
    result := compute(config)
    
    mu.Lock()
    sharedData = result
    mu.Unlock()
}
```

#### 使用细粒度锁
- (代码块)
  - (代码块)
```go
// 粗粒度锁
var globalMu sync.Mutex
var globalData map[string]int

// 细粒度锁（分片）
type Shard struct {
    mu   sync.Mutex
    data map[string]int
}

type ShardedMap []*Shard

func (m ShardedMap) GetShard(key string) *Shard {
    // 哈希分片
    hash := fnv.New32a()
    hash.Write([]byte(key))
    shardIndex := hash.Sum32() % uint32(len(m))
    return m[shardIndex]
}
```

#### 读写锁优化
- (代码块)
  - (代码块)
```go
// 读多写少场景使用RWMutex
var cache = struct {
    mu   sync.RWMutex
    data map[string]string
}{data: make(map[string]string)}

func Get(key string) string {
    cache.mu.RLock()
    defer cache.mu.RUnlock()
    return cache.data[key]
}

func Set(key, value string) {
    cache.mu.Lock()
    defer cache.mu.Unlock()
    cache.data[key] = value
}
```

### 4.2 性能优化实践

#### 4.2.2 Channel优化
- 合理设置缓冲区大小
- 无缓冲channel：适合同步通信，严格顺序
- 有缓冲channel：适合异步通信，减少阻塞
- 缓冲区大小：根据生产者-消费者速度差异设置
- 避免channel泄漏
- (代码块)
  - (代码块)
```go
// 坏：可能泄漏
func badWorker() {
    ch := make(chan int)
    go func() {
        for i := 0; i < 10; i++ {
            ch <- i
        }
    }()
    
    for v := range ch {
        fmt.Println(v)
    }
    // ch未关闭，goroutine可能阻塞
}

// 好：确保关闭
func goodWorker() {
    ch := make(chan int)
    go func() {
        defer close(ch) // 确保关闭
        for i := 0; i < 10; i++ {
            ch <- i
        }
    }()
    
    for v := range ch {
        fmt.Println(v)
    }
}
```

#### 4.2.3 内存优化
- 使用sync.Pool复用对象
```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return make([]byte, 4096)
    },
}

func processRequest(conn net.Conn) {
    buf := bufferPool.Get().([]byte)
    defer func() {
        // 重置buffer防止数据泄露（重要！）
        clear(buf) // Go 1.21+，或用 for i := range buf { buf[i] = 0 }
        bufferPool.Put(buf)
    }()
    n, err := conn.Read(buf)
    if err != nil {
        return
    }
    // 处理 buf[:n]
    _ = n
}
```

#### 4.2.4 避免闭包捕获

> **闭包捕获（Closure Capture）**：闭包"捕获"的是变量的**地址**，不是值。等goroutine执行时，变量可能已经变了。

**电商隐喻：快递单上的地址**
- 快递单上写的是"i的地址"，不是"i的值"
- 等送货时去看地址里的内容，值已经变了

```go
// 错误示例（Go 1.21及以前版本）
for i := 1; i <= 3; i++ {
    go func() {
        fmt.Println("处理订单", i) // 可能全打印4！
    }()
}

// 正确做法：传参复制值
for i := 1; i <= 3; i++ {
    go func(orderID int) {  // 参数传值，复制一份
        fmt.Println("处理订单", orderID)
    }(i)
}
```

> 注：Go 1.22+ 已修复此问题，每次循环迭代创建新变量

### 4.3 并发模式选择

#### CPU密集 vs IO密集

> **CPU密集型（CPU-bound）**：任务一直在计算，CPU是瓶颈
> **IO密集型（IO-bound）**：任务大部分时间在等待，IO是瓶颈

**电商隐喻**

| 类型 | 比喻 | 特点 | goroutine数量建议 |
|------|------|------|-------------------|
| **CPU密集** | 仓库分拣员打包 | 一直干活，不等人 | ≈ CPU核心数 |
| **IO密集** | 快递员等电梯 | 大部分时间在等待 | 可以开很多（几千个） |

**如何判断代码是CPU密集还是IO密集？**

问自己：**代码大部分时间在干什么？**

| 看什么 | CPU密集特征 | IO密集特征 |
|--------|------------|-----------|
| 有没有网络调用 | 没有 http.Get、grpc | 有 http、grpc、tcp |
| 有没有数据库操作 | 没有 db.Query | 有 SQL查询 |
| 有没有文件读写 | 没有 os.ReadFile | 有文件操作 |
| 有没有sleep/等待 | 没有 time.Sleep | 有等待操作 |
| CPU占用 | 100%跑满 | 通常很低 |

**典型例子**

| 类型 | 典型操作 | 电商场景 |
|------|----------|----------|
| **CPU密集** | 循环计算、加密解密、压缩、正则匹配 | 生成缩略图、计算优惠价、密码哈希 |
| **IO密集** | 网络请求、数据库查询、文件读写 | 调用支付API、查库存、发短信 |

```go
// ========== CPU密集型 ==========
// 特征：没有网络/文件/数据库操作，纯计算

func 压缩图片(img []byte) []byte {
    for i := range img {
        img[i] = 复杂算法处理(img[i])  // 一直在算
    }
    return img
}

func 计算优惠价格(order Order) float64 {
    // 复杂的满减、折扣、积分抵扣计算
    return 最终价格
}

// ========== IO密集型 ==========
// 特征：大部分时间在等网络/数据库/文件响应

func 查询物流(orderID string) Status {
    resp, _ := http.Get("https://api.kuaidi.com/" + orderID)  // 等网络
    return 解析(resp)
}

func 查库存(productID int) int {
    row := db.QueryRow("SELECT stock FROM products WHERE id=?", productID)  // 等数据库
    return stock
}
```

**goroutine数量决策**

```go
// CPU密集：goroutine数 ≈ CPU核心数
// 开多了没用，CPU就那么多，反而增加切换开销
workers := runtime.NumCPU()  // 8核就开8个

// IO密集：可以开很多
// 反正大部分时间在等，多开几个能同时等更多请求
for i := 0; i < 1000; i++ {
    go 调用外部API()  // 开1000个都行
}
```

**混合型场景**

实际往往是混合的，按瓶颈分析：

```go
func 处理订单(order Order) {
    库存 := 查库存(order.ProductID)    // IO密集：等数据库
    价格 := 计算优惠价格(order, 库存)    // CPU密集：计算
    调用支付API(order, 价格)           // IO密集：等网络
    生成电子发票PDF(order)             // CPU密集：生成PDF
}
// 大部分时间花在IO → 当IO密集处理
// 如果计算部分特别重 → 把CPU密集部分拆出来用Worker Pool
```

#### Worker Pool模式 —— 工作池

**电商隐喻：仓库分拣线**
- 固定5个分拣员（worker）
- 订单（job）放进队列
- 分拣员从队列取订单处理
- 不会因为1000个订单就招1000个人

**什么时候用？** CPU密集任务，需要控制并发数

```go
func main() {
    jobs := make(chan Order, 100)    // 订单队列
    results := make(chan Result, 100) // 结果队列

    // 启动5个分拣员（固定数量）
    for w := 1; w <= 5; w++ {
        go 分拣员(w, jobs, results)
    }

    // 投递1000个订单
    for i := 1; i <= 1000; i++ {
        jobs <- Order{ID: i}
    }
    close(jobs)
}

func 分拣员(id int, jobs <-chan Order, results chan<- Result) {
    for order := range jobs {
        results <- 打包(order)
    }
}
```

#### Pipeline模式 —— 流水线

**电商隐喻：商品生产线**
```
原料 → 切割 → 组装 → 包装 → 成品
```
每个环节只做一件事，做完传给下一个

**什么时候用？** 数据需要多步处理，每步可以并行

```go
// 阶段1：生成订单
func 接单() <-chan Order {
    out := make(chan Order)
    go func() {
        for i := 1; i <= 10; i++ {
            out <- Order{ID: i}
        }
        close(out)
    }()
    return out
}

// 阶段2：计算价格
func 算价(in <-chan Order) <-chan Order {
    out := make(chan Order)
    go func() {
        for order := range in {
            order.Price = 计算(order)
            out <- order
        }
        close(out)
    }()
    return out
}

// 串起来：接单 → 算价 → 发货
orders := 接单()
priced := 算价(orders)
```

#### Fan-out/Fan-in模式 —— 扇出/扇入

**电商隐喻**

**Fan-out（扇出）= 分单**
- 1000个订单，分给10个仓库同时处理
- 一个输入，多个处理者

**Fan-in（扇入）= 汇总**
- 10个仓库的发货结果，汇总到一个报表
- 多个输入，合并成一个输出

```
        ┌→ 仓库1 ─┐
订单队列 ─┼→ 仓库2 ─┼→ 汇总报表
        └→ 仓库3 ─┘
     (Fan-out)  (Fan-in)
```

**什么时候用？** 任务可以并行处理，最后需要汇总结果

```go
// Fan-out：多个worker抢同一个channel
jobs := make(chan Order, 100)
for i := 0; i < 10; i++ {
    go 仓库处理(jobs, results)  // 10个仓库抢着处理
}

// Fan-in：多个channel合并成一个
func 汇总(channels ...<-chan Result) <-chan Result {
    out := make(chan Result)
    var wg sync.WaitGroup
    for _, ch := range channels {
        wg.Add(1)
        go func(c <-chan Result) {
            defer wg.Done()
            for r := range c {
                out <- r
            }
        }(ch)
    }
    go func() { wg.Wait(); close(out) }()
    return out
}
```

#### 并发模式选择矩阵

| 场景 | 模式 | 电商比喻 |
|------|------|----------|
| 控制并发数 | Worker Pool | 固定5个分拣员 |
| 多步骤处理 | Pipeline | 生产流水线 |
| 并行处理后汇总 | Fan-out/Fan-in | 分单到多仓库，汇总报表 |
| CPU密集任务 | Worker Pool | goroutine数≈CPU核心 |
| IO密集任务 | 直接开goroutine | 可以开很多 |

## 第五部分：死锁问题及解决方案

### 5.1 死锁的四个必要条件

#### 互斥条件（Mutual Exclusion）
- 资源不能同时被多个goroutine使用
- Go中：锁、channel等资源都是互斥的

#### 不可剥夺条件（No Preemption）
- 资源只能由持有者主动释放
- Go中：锁必须由加锁的goroutine解锁，channel中的数据只能通过接收操作取出

#### 请求与保持条件（Hold and Wait）
- 持有至少一个资源，同时请求其他资源
- Go中：持有锁A的同时请求锁B

#### 循环等待条件（Circular Wait）
- 存在一个goroutine等待环
- Go中：goroutine1持有锁A等待锁B，goroutine2持有锁B等待锁A

### 5.2 Go中的死锁场景

#### 5.2.1 Channel死锁
- (代码块)
  - (代码块)
```go
// 无缓冲channel死锁：主goroutine发送，无人接收
func channelDeadlock1() {
    ch := make(chan int)
    ch <- 1 // 主goroutine阻塞，无其他goroutine接收
    // fatal error: all goroutines are asleep - deadlock!
}

// 无缓冲channel死锁：有发送者，无接收者
func channelDeadlock2() {
    ch := make(chan int)
    go func() {
        ch <- 42 // goroutine尝试发送，阻塞等待接收者
    }()
    ch <- 1 // 主goroutine也发送，两个发送者都阻塞，无人接收
}
```

#### 5.2.2 Mutex死锁
- (代码块)
  - (代码块)
```go
// 交叉锁死锁
func mutexDeadlock() {
    var mu1, mu2 sync.Mutex
    
    go func() {
        mu1.Lock()
        defer mu1.Unlock()
        
        time.Sleep(100 * time.Millisecond)
        
        mu2.Lock() // 等待mu2
        defer mu2.Unlock()
    }()
    
    mu2.Lock()
    defer mu2.Unlock()
    
    time.Sleep(50 * time.Millisecond)
    
    mu1.Lock() // 等待mu1，死锁
    defer mu1.Unlock()
}
```

#### 5.2.3 WaitGroup误用（panic与死锁）
- (代码块)
  - (代码块)
```go
// WaitGroup计数错误导致panic
func wgPanic() {
    var wg sync.WaitGroup
    wg.Add(1)
    go func() { wg.Done() }()
    go func() { wg.Done() }() // panic: negative WaitGroup counter
    wg.Wait()
}

// WaitGroup真正的死锁
func wgDeadlock() {
    var wg sync.WaitGroup
    wg.Add(1)
    wg.Wait() // 没有goroutine调用Done()，永远阻塞
}
```

### 5.3 Go死锁检测

#### 运行时死锁检测
- Go运行时会自动检测死锁并panic
- 报错信息：`fatal error: all goroutines are asleep - deadlock!`

#### 竞态条件检测
- (代码块)
  - (代码块)
```bash
go run -race main.go
go test -race
```

### 5.4 死锁解决方案

#### 5.4.1 预防策略
- 1. 按固定顺序获取锁
  - (代码块)
    - (代码块)
```go
// 好：总是按相同顺序获取锁
func safeOperation() {
    mu1.Lock()
    defer mu1.Unlock()
    
    mu2.Lock()
    defer mu2.Unlock()
    
    // 操作共享资源
}
```
- 2. 超时机制（Go 1.18+ TryLock）
  - (代码块)
    - (代码块)
```go
// Go 1.18+ 使用TryLock实现超时获取锁
// 注意：这是自旋等待的简化示例，生产环境建议使用channel+context或semaphore
func tryLockWithTimeout(mu *sync.Mutex, timeout time.Duration) bool {
    deadline := time.Now().Add(timeout)
    for time.Now().Before(deadline) {
        if mu.TryLock() {
            return true
        }
        time.Sleep(time.Millisecond) // 间隔可根据场景调整
    }
    return false
}

// 使用
if tryLockWithTimeout(&mu, 100*time.Millisecond) {
    defer mu.Unlock()
    // 执行操作
} else {
    fmt.Println("获取锁超时")
}
```
- 3. 使用channel限制并发
  - (代码块)
    - (代码块)
```go
func workerPoolWithTimeout() {
    jobs := make(chan Job, 100)
    results := make(chan Result, 100)
    maxWorkers := runtime.NumCPU()
    
    for i := 0; i < maxWorkers; i++ {
        go worker(jobs, results)
    }
    
    // 提交任务
    for i := 0; i < 100; i++ {
        select {
        case jobs <- Job{i}:
            fmt.Printf("Submitted job %d\n", i)
        case <-time.After(10 * time.Millisecond):
            fmt.Printf("Job %d timeout, skipping\n", i)
        }
    }
}
```

#### 5.4.2 检测和解决
- 1. pprof工具分析
  - (代码块)
    - (代码块)
```go
import _ "net/http/pprof"

// 启动HTTP服务器
go func() {
    http.ListenAndServe("localhost:6060", nil)
}()

// 访问：http://localhost:6060/debug/pprof/goroutine?debug=2
// 查看goroutine堆栈，分析死锁
```
- 2. 死锁检测库
```go
// 推荐使用第三方库 github.com/sasha-s/go-deadlock
import "github.com/sasha-s/go-deadlock"

var mu deadlock.Mutex  // 替代 sync.Mutex，自动检测潜在死锁

func example() {
    mu.Lock()
    defer mu.Unlock()
    // 如果检测到死锁风险，会打印警告和堆栈
}
```

#### 5.4.3 恢复策略
- 1. 超时取消（避免goroutine泄漏）
  - (代码块)
    - (代码块)
```go
func operationWithTimeout() {
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()
    
    resultChan := make(chan string, 1) // 缓冲channel防止泄漏
    go func() {
        time.Sleep(3 * time.Second)
        select {
        case resultChan <- "result":
        case <-ctx.Done(): // 超时则直接返回
        }
    }()
    
    select {
    case result := <-resultChan:
        fmt.Println(result)
    case <-ctx.Done():
        fmt.Println("Operation timed out:", ctx.Err())
    }
}
```
- 2. 优雅降级
  - (代码块)
    - (代码块)
```go
func gracefulDegradation() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    
    go monitorSystemHealth(ctx, func() {
        // 系统不健康时触发降级
        cancel()
    })
    
    select {
    case <-doImportantWork(ctx):
        fmt.Println("Work completed successfully")
    case <-ctx.Done():
        fmt.Println("System degraded, skipping non-critical work")
        // 执行降级逻辑
    }
}
```

### 5.5 Go特色死锁解决方案

#### 5.5.1 使用select default避免阻塞
- (代码块)
  - (代码块)
```go
// 好：使用default避免永久阻塞
func nonBlockingSelect() {
    ch := make(chan int)
    
    go func() {
        time.Sleep(100 * time.Millisecond)
        ch <- 42
    }()
    
    select {
    case val := <-ch:
        fmt.Println("Received:", val)
    default:
        fmt.Println("No data available, continuing...")
    }
}
```

#### 5.5.2 Context取消传播
- (代码块)
  - (代码块)
```go
// 通过context传播取消信号
func contextCancellation() {
    ctx, cancel := context.WithCancel(context.Background())
    
    // 启动多个goroutine
    for i := 0; i < 5; i++ {
        go func(id int) {
            select {
            case <-time.After(time.Duration(id) * time.Second):
                fmt.Printf("Worker %d completed\n", id)
            case <-ctx.Done():
                fmt.Printf("Worker %d cancelled: %v\n", id, ctx.Err())
            }
        }(i)
    }
    
    // 2秒后取消所有
    time.Sleep(2 * time.Second)
    cancel()
}
```

#### 5.5.3 使用errgroup简化错误处理
- (代码块)
  - (代码块)
```go
import "golang.org/x/sync/errgroup"

func errgroupExample() {
    var g errgroup.Group
    
    // 启动多个goroutine
    for i := 0; i < 5; i++ {
        i := i // Go 1.21及之前需要此行避免闭包捕获问题，Go 1.22+可省略
        g.Go(func() error {
            if i == 3 {
                return fmt.Errorf("error in worker %d", i)
            }
            fmt.Printf("Worker %d started\n", i)
            time.Sleep(time.Duration(i) * 100 * time.Millisecond)
            fmt.Printf("Worker %d finished\n", i)
            return nil
        })
    }
    
    // 等待所有完成或返回第一个错误
    // 注意：需用errgroup.WithContext(ctx)创建才能自动取消其他goroutine
    if err := g.Wait(); err != nil {
        fmt.Printf("Group error: %v\n", err)
    }
}
```

## 总结
- Go的并发模型通过goroutine和channel提供了一种简单而强大的并发编程方式。理解操作系统层面的多线程知识有助于更好地掌握Go的并发设计。通过遵循最佳实践，避免常见的并发陷阱，可以构建出高性能、高可靠的并发系统。
- Go并发的核心哲学是："不要通过共享内存来通信，而应该通过通信来共享内存"。这一原则贯穿于整个Go并发设计，使得并发编程变得更加简单和安全。

---

## 附录：并发编程词汇表

### 基础概念

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词/相关词 | 反义词/对比词 |
|------|------|------|----------|---------------|---------------|
| **进程** | Process | 操作系统资源分配单位 | 一家店铺 | 任务、应用 | 线程 |
| **线程** | Thread | CPU调度基本单位 | 店铺里的员工 | 执行流 | 进程 |
| **协程** | Coroutine | 用户态轻量级线程 | 临时工（成本低） | goroutine、纤程 | 线程 |
| **goroutine** | - | Go的协程实现 | 临时工 | 协程、轻量级线程 | OS线程 |

### 并发 vs 并行

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **并发** | Concurrency | 逻辑上同时处理多个任务 | 一个客服切换处理多个客户 | 多任务 | 串行 |
| **并行** | Parallelism | 物理上同时执行多个任务 | 多个客服同时服务 | 同时执行 | 串行 |
| **串行** | Serial | 一个接一个执行 | 排队一个个处理 | 顺序执行 | 并发、并行 |

### 同步与通信

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **同步** | Synchronous | 等待结果返回才继续 | 柜台结账，站着等 | 阻塞式 | 异步 |
| **异步** | Asynchronous | 不等结果，继续执行 | 取号等餐，拿号就走 | 非阻塞式 | 同步 |
| **阻塞** | Blocking | 等待时什么都不能做 | 排队时干站着 | 挂起、等待 | 非阻塞 |
| **非阻塞** | Non-blocking | 等待时可以做别的事 | 等餐时可以逛街 | 轮询、异步 | 阻塞 |

### Channel相关

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **无缓冲channel** | Unbuffered | 发送接收必须同时就绪 | 一对一客服 | 同步channel | 有缓冲channel |
| **有缓冲channel** | Buffered | 有队列暂存数据 | 快递柜 | 异步channel | 无缓冲channel |
| **只发送channel** | Send-only | 只能发送的channel | 订单投递口 | chan<- | 只接收channel |
| **只接收channel** | Receive-only | 只能接收的channel | 仓库取单窗口 | <-chan | 只发送channel |

### 锁与同步原语

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **互斥锁** | Mutex | 同一时间只有一个能访问 | 试衣间 | 排他锁、独占锁 | 读写锁 |
| **读写锁** | RWMutex | 读共享，写独占 | 商品详情页 | 读写互斥锁 | 纯互斥锁 |
| **死锁** | Deadlock | 互相等待，永远阻塞 | A等B开门，B等A开门 | 互锁 | 活锁 |
| **活锁** | Livelock | 不断重试，无法进展 | 两人互相让路 | - | 死锁 |
| **饥饿** | Starvation | 长期无法获得资源 | 一直被插队 | - | 公平调度 |

### 内存模型

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **happens-before** | - | A的结果对B可见的保证 | 发货签收顺序 | 先行发生 | - |
| **可见性** | Visibility | 一个线程的修改对其他线程可见 | 仓库改价格，前台能看到 | - | 缓存不一致 |
| **原子性** | Atomicity | 操作不可分割 | 扣款不能中途打断 | 不可中断 | 非原子操作 |
| **有序性** | Ordering | 指令按预期顺序执行 | 先扣库存再扣款 | 顺序性 | 指令重排序 |

### 并发模式

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **Worker Pool** | 工作池 | 固定数量worker处理任务 | 仓库5个分拣员 | 线程池、协程池 | 无限并发 |
| **Pipeline** | 流水线 | 多阶段串行处理 | 生产流水线 | 管道模式 | 批处理 |
| **Fan-out** | 扇出 | 一个输入分发给多个处理者 | 分单给多仓库 | 分发、广播 | Fan-in |
| **Fan-in** | 扇入 | 多个输入合并成一个输出 | 多仓库汇总报表 | 汇聚、合并 | Fan-out |

### 任务类型

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **CPU密集型** | CPU-bound | 任务一直在计算 | 分拣员打包 | 计算密集型 | IO密集型 |
| **IO密集型** | IO-bound | 任务大部分时间在等待IO | 快递员等电梯 | 等待密集型 | CPU密集型 |

### 其他重要概念

| 术语 | 英文 | 含义 | 电商隐喻 | 同义词 | 反义词 |
|------|------|------|----------|--------|--------|
| **闭包捕获** | Closure Capture | 闭包引用外部变量的地址 | 快递单写地址不写内容 | 变量捕获 | 值传递 |
| **竞态条件** | Race Condition | 多线程访问共享资源结果不确定 | 两人同时抢最后一件商品 | 数据竞争 | 线程安全 |
| **背压** | Backpressure | 下游告诉上游"慢点" | 仓库满了，暂停收单 | 流量控制 | 无限缓冲 |
| **context** | 上下文 | 传递取消信号和超时 | 外卖配送超时机制 | 取消令牌 | - |
| **CSP** | Communicating Sequential Processes | 通过消息传递进行通信的并发模型 | 用传递代替共享 | 消息传递 | 共享内存 |

### 缩写对照

| 缩写 | 全称 | 含义 |
|------|------|------|
| **GMP** | Goroutine-Machine-Processor | Go调度器模型 |
| **CSP** | Communicating Sequential Processes | 通信顺序进程 |
| **CAS** | Compare-And-Swap | 原子操作：比较并交换 |
| **MESI** | Modified-Exclusive-Shared-Invalid | CPU缓存一致性协议 |

### Java 锁概念与 Go 对照

> 本节对比 Java 的锁机制与 Go 的实现差异，帮助有 Java 背景的开发者快速理解 Go 并发。

#### 概念对照总表

| Java 概念 | Go 对应 | 说明 |
|-----------|---------|------|
| 重量级锁/轻量级锁 | ❌ 无 | Go 没有锁升级机制 |
| 乐观锁 | ✅ `sync/atomic` | CAS 操作 |
| 悲观锁 | ✅ `sync.Mutex` | 直接阻塞 |
| 排他锁 | ✅ `sync.Mutex` / `RWMutex.Lock()` | 独占 |
| 共享锁 | ✅ `sync.RWMutex.RLock()` | 读共享 |
| 公平锁 | ⚠️ 部分 | Mutex 饥饿模式（自动） |
| 非公平锁 | ⚠️ 部分 | Mutex 正常模式（自动） |
| 可重入锁 | ❌ **不支持** | 同goroutine重复Lock会死锁！ |
| synchronized锁升级 | ❌ 无 | Go 无此优化 |
| 锁粗化 | ❌ 无 | Go 无 JIT，需手动优化 |

#### 1. 重量级锁 vs 轻量级锁

**Java synchronized 锁升级**：
```
无锁 → 偏向锁 → 轻量级锁 → 重量级锁
       ↑          ↑           ↑
    无竞争     CAS失败     自旋失败
```

**Go 的设计**：
- Go 没有锁升级机制
- Mutex 只有两种模式：正常模式 ⟷ 饥饿模式
- 正常模式：先自旋几次，失败后阻塞
- 饥饿模式：直接排队，防止goroutine饿死

```go
// Go 的替代方案：根据场景选择不同工具
atomic.AddInt32(&counter, 1)  // 无锁，类似"轻量级"
mu.Lock()                      // 有锁，类似"重量级"
```

> **Go 设计哲学**：简单直接，不搞隐式优化。想要轻量级？用 atomic。想要互斥？用 Mutex。

#### 2. 乐观锁 vs 悲观锁

| 类型 | Java | Go |
|------|------|-----|
| 悲观锁 | `synchronized` / `ReentrantLock` | `sync.Mutex` |
| 乐观锁 | `AtomicInteger` / `StampedLock` | `sync/atomic` |

```go
// 悲观锁
mu.Lock()
counter++
mu.Unlock()

// 乐观锁（CAS）
atomic.AddInt32(&counter, 1)

// 手动 CAS 循环
for {
    old := atomic.LoadInt32(&counter)
    if atomic.CompareAndSwapInt32(&counter, old, old+1) {
        break
    }
}
```

#### 3. 公平锁 vs 非公平锁

**Java**：可手动选择
```java
ReentrantLock fairLock = new ReentrantLock(true);   // 公平
ReentrantLock unfairLock = new ReentrantLock(false); // 非公平
```

**Go**：自动切换，无法手动控制
- **正常模式（类似非公平）**：新来的goroutine可能抢到锁，性能好
- **饥饿模式（类似公平）**：等待超过1ms自动切换，锁直接交给队首

#### 4. 可重入锁（重要区别！）

**Java**：天然支持
```java
synchronized void outer() {
    inner();  // ✅ 同一线程可重入
}
synchronized void inner() { }
```

**Go**：❌ 不支持，会死锁！
```go
var mu sync.Mutex

func outer() {
    mu.Lock()
    defer mu.Unlock()
    inner()  // 💀 死锁！
}

func inner() {
    mu.Lock()  // 永远阻塞
    defer mu.Unlock()
}
```

**Go 的解决方案**：
```go
// 方案1：重构代码，内部函数不加锁
func outer() {
    mu.Lock()
    defer mu.Unlock()
    innerLocked()  // 约定：调用者已持有锁
}

func innerLocked() {
    // 不加锁，假设调用者已持有
}

// 方案2：拆分锁的粒度
// 方案3：使用 channel 替代锁
```

#### 5. 锁粗化（Lock Coarsening）

**Java**：JIT 自动优化
```java
// JIT 会自动把循环内的锁提到循环外
for (int i = 0; i < 100; i++) {
    synchronized (obj) { list.add(i); }
}
// 优化为 ↓
synchronized (obj) {
    for (int i = 0; i < 100; i++) { list.add(i); }
}
```

**Go**：需手动优化
```go
// 坏：频繁加锁解锁
for i := 0; i < 100; i++ {
    mu.Lock()
    list = append(list, i)
    mu.Unlock()
}

// 好：手动粗化
mu.Lock()
for i := 0; i < 100; i++ {
    list = append(list, i)
}
mu.Unlock()
```

#### 6. Go 没有的 Java 特性

| Java 特性 | 说明 | Go 替代方案 |
|-----------|------|-------------|
| 偏向锁 | 无竞争时零开销 | 无，用 atomic 或避免共享 |
| 锁消除 | JIT 检测到无竞争时移除锁 | 无 JIT，编译器逃逸分析有限 |
| 锁升级 | 根据竞争自动升级 | 手动选择 atomic/Mutex |
| 可重入 | 同线程可多次获取 | 不支持，需重构代码 |
| Condition | 条件变量 | `sync.Cond`（功能类似） |
| StampedLock | 乐观读锁 | 无直接对应，用 atomic.Value |

#### Go 的设计哲学

> **显式优于隐式**：
> - 不搞复杂的锁升级，让程序员明确选择工具
> - 不支持可重入，避免隐藏的复杂性和递归锁的性能问题
> - 推荐用 Channel 替代锁，从设计上避免锁问题
>
> **"Don't communicate by sharing memory; share memory by communicating."**