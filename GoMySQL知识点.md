# Go MySQL 知识点

> **作者**: frank.hutiefang
> **知乎**: @大大大大大芳
> **微信**: hutiefang
> **版本**: v1.1
> **更新时间**: 2026-02-04


---

## 第一部分：数据库基础

### 1.1 数据库定义

#### 核心概念
- **数据库(Database)**：按照数据结构组织、存储和管理数据的仓库，长期存储在计算机内的、有组织的、可共享的、统一管理的大量数据集合
- **数据库管理系统(DBMS)**：管理数据库的软件系统，如 MySQL、PostgreSQL、Oracle
- **持久化**：将内存中的数据保存到磁盘，断电不丢失

#### SQL ANSI/ISO 标准演进

SQL 于 1986 年被 ANSI 采纳为标准，1987 年被 ISO 采纳。至今已发布 9 个主要版本。

##### 标准版本与主要特性

| 版本 | 年份 | 主要特性 | MySQL 支持 |
|------|------|----------|------------|
| **SQL-86** | 1986 | 首个标准，基础 SELECT/INSERT/UPDATE/DELETE | ✅ |
| **SQL-89** | 1989 | PRIMARY KEY、FOREIGN KEY、DEFAULT、CHECK 约束 | ✅ |
| **SQL-92** | 1992 | **里程碑版本**：JOIN 语法、LEFT/RIGHT/FULL JOIN、DATE/TIME/TIMESTAMP、CASE 表达式、CAST 类型转换 | ✅ (无 FULL JOIN) |
| **SQL:1999** | 1999 | CTE (WITH)、递归查询、BOOLEAN 类型、正则表达式、触发器、存储过程、用户自定义类型 | ✅ 8.0+ (CTE) |
| **SQL:2003** | 2003 | **窗口函数** (ROW_NUMBER, RANK)、MERGE 语句、XML 支持、SEQUENCE、MULTISET | ⚠️ 8.0+ (窗口函数)，❌ MERGE |
| **SQL:2006** | 2006 | SQL/XML 增强、XQuery 支持 | ⚠️ 部分 |
| **SQL:2008** | 2008 | TRUNCATE TABLE、INSTEAD OF 触发器、ORDER BY 增强 | ✅ TRUNCATE |
| **SQL:2011** | 2011 | **时态表** (System-Versioned / Application-Time)、窗口函数增强 | ❌ 时态表 |
| **SQL:2016** | 2016 | **JSON 支持** (JSON_OBJECT, JSON_ARRAY)、行模式识别 (MATCH_RECOGNIZE)、多态表函数 | ✅ 8.0+ JSON，❌ MATCH_RECOGNIZE |
| **SQL:2023** | 2023 | **图查询 (SQL/PGQ)**、JSON 原生类型、数字下划线 (1_000_000)、BTRIM 函数 | ❌ 图查询，❌ 数字下划线 |

> 参考：[ISO/IEC 9075 - Wikipedia](https://en.wikipedia.org/wiki/ISO/IEC_9075)、[SQL:2023 - Wikipedia](https://en.wikipedia.org/wiki/SQL:2023)

##### MySQL 不支持的重要 SQL 标准特性

| 特性 | SQL 标准版本 | 说明 | 替代方案 |
|------|-------------|------|----------|
| **FULL OUTER JOIN** | SQL-92 | 全外连接 | LEFT JOIN UNION RIGHT JOIN |
| **MERGE (UPSERT)** | SQL:2003 | 合并插入/更新 | INSERT ... ON DUPLICATE KEY UPDATE |
| **时态表** | SQL:2011 | 系统版本化表、时间旅行查询 | 手动维护历史表 / MariaDB 支持 |
| **MATCH_RECOGNIZE** | SQL:2016 | 行模式识别（正则匹配行序列） | 应用层处理 / Oracle 支持 |
| **图查询 SQL/PGQ** | SQL:2023 | 图数据库查询语法 | Neo4j / 多表 JOIN |
| **数字下划线** | SQL:2023 | `1_000_000` 表示百万 | 直接写 `1000000` |
| **BOOLEAN 字面量** | SQL:1999 | TRUE/FALSE 作为值 | ✅ MySQL 支持但存储为 TINYINT(1) |

##### 各标准版本示例

```sql
-- SQL-92: JOIN 语法
SELECT * FROM emp e
LEFT JOIN dept d ON e.dept_id = d.id;

-- SQL:1999: CTE (MySQL 8.0+)
WITH RECURSIVE org_tree AS (
    SELECT id, name, manager_id, 1 AS level FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.manager_id, t.level + 1
    FROM employees e JOIN org_tree t ON e.manager_id = t.id
)
SELECT * FROM org_tree;

-- SQL:2003: 窗口函数 (MySQL 8.0+)
SELECT name, salary,
       ROW_NUMBER() OVER (ORDER BY salary DESC) AS rank,
       SUM(salary) OVER () AS total
FROM employees;

-- SQL:2016: JSON 函数 (MySQL 8.0+)
SELECT JSON_OBJECT('id', id, 'name', name) AS user_json FROM users;

-- SQL:2003 MERGE (MySQL 不支持，用以下替代)
-- 标准写法: MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...
-- MySQL 替代:
INSERT INTO target (id, name) VALUES (1, 'test')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- SQL:2011 时态表 (MySQL 不支持，MariaDB 支持)
-- CREATE TABLE t (id INT, name VARCHAR(100)) WITH SYSTEM VERSIONING;
-- SELECT * FROM t FOR SYSTEM_TIME AS OF '2024-01-01';
```

### 1.2 三大范式

| 范式 | 定义 | 示例 |
|------|------|------|
| **1NF** | 每列值不可再分解（原子性） | "北京,上海" 需拆分为独立字段 |
| **2NF** | 非主属性完全依赖于主键（消除部分依赖） | 复合主键(订单ID+商品ID)，客户姓名应独立成表 |
| **3NF** | 非主属性直接依赖主键（消除传递依赖） | 订单表中的客户地址应移至客户表 |

#### 反范式设计

适用场景：
- **提高灵活性**：使用 JSON 字段存储可变配置
- **提升性能**：冗余字段避免 JOIN
- **快速查询**：存储统计数据（如总消费金额）

```go
// Go 中处理 JSON 字段
type User struct {
    ID     int64           `db:"id"`
    Name   string          `db:"name"`
    Config json.RawMessage `db:"config"` // 存储灵活配置
}

type UserConfig struct {
    Gender      string   `json:"gender"`
    Province    string   `json:"province"`
    BestSubject []int    `json:"best_subject"`
}
```

### 1.3 数据库分类

#### 按数据模型分类

| 类型 | 代表产品 | 特点 |
|------|----------|------|
| 关系型(SQL) | MySQL, PostgreSQL, Oracle | ACID 事务、SQL 查询 |
| 键值型 | Redis, Etcd | 高性能缓存、简单数据结构 |
| 文档型 | MongoDB | 灵活 Schema、JSON 存储 |
| 列式存储 | ClickHouse, HBase | 聚合查询快、OLAP 场景 |
| 时序数据库 | InfluxDB, TDengine | 时间序列数据、IoT 场景 |
| 图数据库 | Neo4j | 关系网络、社交图谱 |

#### 按事务特性分类

| 类型 | 说明 | 代表产品 |
|------|------|----------|
| **OLTP** | 事务处理，强一致性 | MySQL, PostgreSQL |
| **OLAP** | 分析处理，弱事务 | ClickHouse, Doris |
| **HTAP** | 混合型，同时支持 TP/AP | TiDB, OceanBase |

#### SQL vs NoSQL vs NewSQL

##### 三者对比

| 特性 | SQL (关系型) | NoSQL (非关系型) | NewSQL (新型关系型) |
|------|-------------|-----------------|-------------------|
| **数据模型** | 表、行、列 | 键值/文档/列族/图 | 表、行、列 |
| **Schema** | 固定 Schema | 灵活/无 Schema | 固定 Schema |
| **事务** | 完整 ACID | 通常无/弱事务 | 完整 ACID |
| **扩展方式** | 垂直扩展（Scale Up） | 水平扩展（Scale Out） | 水平扩展 + ACID |
| **一致性** | 强一致性 | 最终一致性 | 强一致性 |
| **查询语言** | SQL | 各自 API | SQL 兼容 |
| **适用场景** | 事务、复杂查询 | 高并发、大数据量 | 分布式事务 |

##### SQL（关系型数据库）


**优点**：
- ACID 事务保证数据一致性
- SQL 标准化，学习成本低
- 支持复杂 JOIN 和聚合查询
- 数据完整性约束（外键、唯一等）

**缺点**：
- 垂直扩展有上限
- Schema 变更成本高
- 高并发写入性能瓶颈

**适用场景**：金融交易、订单系统、ERP、需要事务保证的业务

##### NoSQL（非关系型数据库）


**优点**：
- 水平扩展能力强
- Schema 灵活，快速迭代（重要）
- 高并发读写性能好（重要）
- 适合非结构化数据

**缺点**：
- 不支持或弱支持事务
- 不支持复杂 JOIN
- 数据一致性较弱
- 缺乏统一查询标准

**CAP 定理**：分布式系统只能同时满足其中两项
- **C (Consistency)**：一致性
- **A (Availability)**：可用性
- **P (Partition Tolerance)**：分区容错性

| 选择 | 说明 | 代表 |
|------|------|------|
| CP | 强一致，可能不可用 | HBase, MongoDB |
| AP | 高可用，最终一致 | Cassandra, DynamoDB |
| CA | 单机，无分区 | 传统关系型数据库 |

##### NewSQL（新型分布式关系型）


**核心特点**：
- **SQL 兼容**：支持标准 SQL，无学习成本
- **分布式 ACID**：跨节点事务保证
- **水平扩展**：自动分片，线性扩展
- **高可用**：多副本，自动故障转移

**对比传统分库分表**：

| 特性 | 分库分表 | NewSQL |
|------|----------|--------|
| 事务 | 需要分布式事务中间件 | 原生支持 |
| 扩容 | 手动迁移数据 | 自动 Rebalance |
| 运维 | 复杂 | 相对简单 |
| SQL | 受限（跨库 JOIN 难） | 完整支持 |

**典型产品对比**：

| 产品 | 公司 | 兼容协议 | 特点 |
|------|------|----------|------|
| **TiDB** | PingCAP | MySQL | 开源、HTAP、Raft |
| **OceanBase** | 蚂蚁 | MySQL/Oracle | 金融级、Paxos |
| **CockroachDB** | Cockroach Labs | PostgreSQL | 全球分布、Raft |
| **Spanner** | Google | 自有 | TrueTime、全球一致 |

**适用场景**：
- 传统数据库扩展瓶颈
- 需要分布式事务
- 不想改造应用（SQL 兼容）
- 金融、电商等高可用场景

##### 如何选择？

| 场景 | 推荐 |
|------|------|
| 强事务、复杂查询、数据量中等 | MySQL/PostgreSQL |
| 高并发缓存、简单 KV | Redis |
| 灵活 Schema、文档存储 | MongoDB |
| 海量数据分析、时序 | ClickHouse/HBase |
| 分布式事务、水平扩展 | TiDB/OceanBase |
| 社交关系、图计算 | Neo4j |

### 1.4 主流关系数据库

| 数据库 | 特点 | 适用场景 |
|--------|------|----------|
| **MySQL** | 开源免费、生态成熟 | 互联网应用、中小型系统 |
| **PostgreSQL** | SQL 标准完善、扩展性强 | 复杂查询、GIS、信创 |
| **Oracle** | 商业支持、性能强劲 | 大型企业、金融、银行 |
| **SQLite** | 嵌入式、零配置 | 移动端、本地存储 |

#### MySQL 版本选择

| 版本 | 说明 |
|------|------|
| **社区版 (GPL)** | 免费，适合大多数场景。GPL 协议要求：修改源码需开源，但作为独立服务使用不受影响 |
| **企业版** | 付费，提供商业支持和高级功能 |
| **MariaDB** | MySQL 创始人的分支，某些场景性能更优 |

### 1.5 SQL 语言分类

| 类型 | 全称 | 功能 | 示例 |
|------|------|------|------|
| **DDL** | Data Definition Language | 定义数据结构 | CREATE, ALTER, DROP, TRUNCATE |
| **DML** | Data Manipulation Language | 操作数据 | SELECT, INSERT, UPDATE, DELETE |
| **DCL** | Data Control Language | 权限控制 | GRANT, REVOKE, DENY |
| **TCL** | Transaction Control Language | 事务控制 | COMMIT, ROLLBACK, SAVEPOINT |

```sql
-- DDL: 创建表
CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));

-- DML: 插入数据
INSERT INTO users (id, name) VALUES (1, 'frank');

-- DCL: 授权
GRANT SELECT, INSERT ON testdb.* TO 'app_user'@'%';

-- TCL: 事务
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
SAVEPOINT sp1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

---

## 第二部分：Go 连接 MySQL

### 2.1 database/sql 标准库

Go 标准库 `database/sql` 提供统一的数据库访问接口，配合驱动使用。

```go
import (
    "database/sql"
    _ "github.com/go-sql-driver/mysql" // MySQL 驱动
)

func main() {
    // DSN 格式: user:password@tcp(host:port)/dbname?params
    dsn := "root:password@tcp(127.0.0.1:3306)/testdb?charset=utf8mb4&parseTime=true&loc=Local"

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    // 连接池配置
    db.SetMaxOpenConns(100)           // 最大连接数
    db.SetMaxIdleConns(10)            // 最大空闲连接数
    db.SetConnMaxLifetime(time.Hour)  // 连接最大生命周期
    db.SetConnMaxIdleTime(10 * time.Minute) // 空闲连接超时

    // 验证连接
    if err := db.Ping(); err != nil {
        log.Fatal(err)
    }
}
```

#### 基本 CRUD 操作

```go
// 查询单行
func getUser(db *sql.DB, id int64) (*User, error) {
    var user User
    err := db.QueryRow("SELECT id, name, age FROM users WHERE id = ?", id).
        Scan(&user.ID, &user.Name, &user.Age)
    if err == sql.ErrNoRows {
        return nil, nil // 未找到
    }
    return &user, err
}

// 查询多行
func listUsers(db *sql.DB, limit int) ([]User, error) {
    rows, err := db.Query("SELECT id, name, age FROM users LIMIT ?", limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name, &u.Age); err != nil {
            return nil, err
        }
        users = append(users, u)
    }
    return users, rows.Err()
}

// 插入
func createUser(db *sql.DB, name string, age int) (int64, error) {
    result, err := db.Exec("INSERT INTO users (name, age) VALUES (?, ?)", name, age)
    if err != nil {
        return 0, err
    }
    return result.LastInsertId()
}

// 更新
func updateUser(db *sql.DB, id int64, name string) (int64, error) {
    result, err := db.Exec("UPDATE users SET name = ? WHERE id = ?", name, id)
    if err != nil {
        return 0, err
    }
    return result.RowsAffected()
}
```

### 2.2 sqlx 增强库

`sqlx` 是 `database/sql` 的扩展，提供结构体映射、命名参数等功能。

```go
import "github.com/jmoiron/sqlx"

type User struct {
    ID        int64     `db:"id"`
    Name      string    `db:"name"`
    Age       int       `db:"age"`
    CreatedAt time.Time `db:"created_at"`
}

func main() {
    db, err := sqlx.Connect("mysql", dsn)
    if err != nil {
        log.Fatal(err)
    }

    // 查询到结构体
    var user User
    err = db.Get(&user, "SELECT * FROM users WHERE id = ?", 1)

    // 查询到切片
    var users []User
    err = db.Select(&users, "SELECT * FROM users WHERE age > ?", 18)

    // 命名参数查询
    rows, err := db.NamedQuery(`SELECT * FROM users WHERE name = :name`,
        map[string]interface{}{"name": "frank"})

    // 命名参数插入
    _, err = db.NamedExec(`INSERT INTO users (name, age) VALUES (:name, :age)`,
        User{Name: "alice", Age: 25})
}
```

### 2.3 GORM ORM 框架

GORM 是 Go 最流行的 ORM 框架，支持自动迁移、关联、Hook 等特性。

```go
import "gorm.io/gorm"
import "gorm.io/driver/mysql"

type User struct {
    ID        uint           `gorm:"primaryKey"`
    Name      string         `gorm:"size:100;not null"`
    Age       int            `gorm:"default:0"`
    Email     *string        `gorm:"uniqueIndex"`
    CreatedAt time.Time
    UpdatedAt time.Time
    DeletedAt gorm.DeletedAt `gorm:"index"` // 软删除
}

func main() {
    dsn := "root:password@tcp(127.0.0.1:3306)/testdb?charset=utf8mb4&parseTime=true&loc=Local"
    db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
    if err != nil {
        log.Fatal(err)
    }

    // 自动迁移
    db.AutoMigrate(&User{})

    // 创建
    user := User{Name: "frank", Age: 30}
    db.Create(&user)

    // 查询
    var result User
    db.First(&result, 1)                          // 主键查询
    db.First(&result, "name = ?", "frank")        // 条件查询
    db.Where("age > ?", 18).Find(&users)          // 多条查询

    // 更新
    db.Model(&user).Update("name", "alice")       // 单字段
    db.Model(&user).Updates(User{Name: "bob", Age: 25}) // 多字段

    // 删除
    db.Delete(&user, 1)  // 软删除（如果有 DeletedAt 字段）
    db.Unscoped().Delete(&user, 1) // 硬删除
}
```

#### GORM 连接池配置

```go
sqlDB, err := db.DB()
if err != nil {
    log.Fatal(err)
}

sqlDB.SetMaxIdleConns(10)
sqlDB.SetMaxOpenConns(100)
sqlDB.SetConnMaxLifetime(time.Hour)
```

#### GORM 面试高频知识点

##### 1. GORM v1 vs v2 区别

| 区别 | v1 | v2 |
|------|-----|-----|
| 导入路径 | `github.com/jinzhu/gorm` | `gorm.io/gorm` |
| 驱动 | 内置 | 独立包 `gorm.io/driver/mysql` |
| Hook 签名 | 多种 | 统一 `func(tx *gorm.DB) error` |
| 软删除 | `DeletedAt` 自动启用 | 需用 `gorm.DeletedAt` 类型 |

##### 2. 零值更新问题

**问题**：`Updates(struct)` 忽略零值（`0`、`""`、`false`）

**解决方案**：
- 使用 `map[string]interface{}`
- 使用 `Select("字段名")` 指定更新字段
- 使用 `Select("*")` 更新所有字段

##### 3. Save vs Updates 区别

| 方法 | 零值处理 |
|------|----------|
| `Save` | ✅ 更新零值（全字段保存） |
| `Updates(struct)` | ❌ 忽略零值 |
| `Updates(map)` | ✅ 更新零值 |

##### 4. Hook 钩子函数

**定义**：CRUD 操作前后自动执行的回调函数

**执行顺序**：
- 创建：BeforeSave → BeforeCreate → **插入** → AfterCreate → AfterSave
- 更新：BeforeSave → BeforeUpdate → **更新** → AfterUpdate → AfterSave
- 删除：BeforeDelete → **删除** → AfterDelete

**用途**：密码加密、数据校验、记录日志、权限检查

##### 5. 软删除（Soft Delete）

- 需定义 `DeletedAt gorm.DeletedAt` 字段
- `Delete()` 只设置 deleted_at，不真删
- 查询自动过滤已删除记录
- `Unscoped()` 查询/删除包含已删除记录

##### 6. 预加载 Preload vs Joins

| 方式 | SQL 次数 | 适用关系 |
|------|----------|----------|
| `Preload` | 多次（N+1 优化为 2 次） | 一对多、多对多 |
| `Joins` | 单次（LEFT JOIN） | 仅一对一 |

##### 7. 四种关联关系

| 类型 | 含义 | 示例 |
|------|------|------|
| Belongs To | 属于 | 订单属于用户 |
| Has One | 拥有一个 | 用户有一个档案 |
| Has Many | 拥有多个 | 用户有多个订单 |
| Many2Many | 多对多 | 用户和角色 |

##### 8. AutoMigrate 限制

- ✅ 支持：建表、添加字段
- ❌ 不支持：修改字段类型、删除字段（防止数据丢失）

##### 9. 查询不到数据处理

- 返回 `gorm.ErrRecordNotFound` 错误
- 用 `errors.Is(err, gorm.ErrRecordNotFound)` 判断
- 或检查 `result.RowsAffected == 0`

##### 10. 常见踩坑

| 问题 | 解决方案 |
|------|----------|
| 时间字段报错 | DSN 加 `parseTime=true` |
| 零值不更新 | 用 map 或 Select |
| 表名多了 s | 配置 `SingularTable: true` |
| 无条件删除报错 | 必须加 Where 条件 |
| 关联不加载 | 使用 Preload |

### 2.4 事务处理

#### database/sql 事务

```go
func transferMoney(db *sql.DB, fromID, toID int64, amount float64) error {
    tx, err := db.Begin()
    if err != nil {
        return err
    }
    // defer 确保异常时回滚
    defer func() {
        if p := recover(); p != nil {
            tx.Rollback()
            panic(p)
        }
    }()

    // 扣款
    _, err = tx.Exec("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, fromID)
    if err != nil {
        tx.Rollback()
        return err
    }

    // 入账
    _, err = tx.Exec("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, toID)
    if err != nil {
        tx.Rollback()
        return err
    }

    return tx.Commit()
}
```

#### GORM 事务

```go
// 方式一：手动事务
tx := db.Begin()
defer func() {
    if r := recover(); r != nil {
        tx.Rollback()
    }
}()

if err := tx.Create(&user).Error; err != nil {
    tx.Rollback()
    return err
}
tx.Commit()

// 方式二：自动事务（推荐）
err := db.Transaction(func(tx *gorm.DB) error {
    if err := tx.Create(&user).Error; err != nil {
        return err // 返回错误自动回滚
    }
    if err := tx.Create(&order).Error; err != nil {
        return err
    }
    return nil // 返回 nil 自动提交
})
```

### 2.5 批量操作

#### 批量插入

```go
// sqlx 批量插入
func batchInsertUsers(db *sqlx.DB, users []User) error {
    query := `INSERT INTO users (name, age) VALUES (:name, :age)`
    _, err := db.NamedExec(query, users)
    return err
}

// GORM 批量插入
func batchInsertUsersGORM(db *gorm.DB, users []User) error {
    return db.CreateInBatches(users, 100).Error // 每批 100 条
}

// 原生 SQL 批量插入（性能最优）
func batchInsertRaw(db *sql.DB, users []User) error {
    if len(users) == 0 {
        return nil
    }

    valueStrings := make([]string, 0, len(users))
    valueArgs := make([]interface{}, 0, len(users)*2)

    for _, u := range users {
        valueStrings = append(valueStrings, "(?, ?)")
        valueArgs = append(valueArgs, u.Name, u.Age)
    }

    query := fmt.Sprintf("INSERT INTO users (name, age) VALUES %s",
        strings.Join(valueStrings, ","))

    _, err := db.Exec(query, valueArgs...)
    return err
}
```

#### LOAD DATA INFILE（最快）

```go
// 先生成 CSV 文件，再用 LOAD DATA 导入
func loadDataInfile(db *sql.DB, filePath string) error {
    query := fmt.Sprintf(`
        LOAD DATA LOCAL INFILE '%s'
        INTO TABLE users
        FIELDS TERMINATED BY ','
        LINES TERMINATED BY '\n'
        (name, age)
    `, filePath)

    _, err := db.Exec(query)
    return err
}
```

---

## 第三部分：MySQL 原理

### 3.1 MySQL 版本与发布策略

#### 版本发布策略（2024 年起）

MySQL 采用双轨发布策略：

| 类型 | 代表版本 | 特点 | 支持周期 | 适用场景 |
|------|----------|------|----------|----------|
| **LTS (长期支持)** | 8.4.x | 稳定、无功能移除、仅修复 | 5年Premier + 3年Extended | 生产环境、企业级 |
| **Innovation (创新)** | 9.x | 新特性、快速迭代 | 到下个版本发布 | 开发测试、尝鲜 |

> **升级路径**：8.4 LTS → 9.x Innovation → 下一个 LTS（预计 9.7 LTS）
>
> 参考：[MySQL Releases: Innovation and LTS](https://dev.mysql.com/doc/refman/9.1/en/mysql-releases.html)

#### 版本特性对比

| 特性 | MySQL 5.7 | MySQL 8.0/8.4 LTS | MySQL 9.x |
|------|-----------|-------------------|-----------|
| **发布时间** | 2015 | 8.0: 2018 / 8.4: 2024 | 9.0: 2024-07 |
| **支持状态** | ⚠️ EOL (2023-10) | ✅ 当前 LTS | ✅ Innovation |
| **默认字符集** | latin1 | utf8mb4 | utf8mb4 |
| **默认认证插件** | mysql_native_password | caching_sha2_password | caching_sha2_password |
| **mysql_native_password** | ✅ 默认 | ⚠️ 弃用 | ❌ **已移除** |
| **窗口函数** | ❌ | ✅ | ✅ |
| **CTE (WITH)** | ❌ | ✅ | ✅ |
| **JSON 函数** | 基础 | 完整 | 完整 |
| **隐藏索引** | ❌ | ✅ | ✅ 默认不可见 |
| **函数索引** | ❌ | ✅ | ✅ |
| **降序索引** | ❌ | ✅ | ✅ |
| **VECTOR 类型** | ❌ | ❌ | ✅ **新增** |
| **JavaScript 存储过程** | ❌ | ❌ | ✅ 企业版 |

#### MySQL 9 重要变更

##### 新增特性

| 特性 | 说明 | 版本 |
|------|------|------|
| **VECTOR 数据类型** | 支持向量存储，用于 AI/ML 场景 | 9.0+ |
| **JavaScript 存储过程** | 使用 JS 编写存储过程（企业版） | 9.0+ |
| **新索引默认不可见** | 创建索引后默认 INVISIBLE，防止意外影响查询计划 | 9.0+ |
| **性能提升** | 读写性能提升约 7-40%（场景相关） | 9.0+ |

##### VECTOR 数据类型

```sql
-- MySQL 9.0+ 支持向量类型，用于 AI/机器学习场景
CREATE TABLE embeddings (
    id INT PRIMARY KEY,
    embedding VECTOR(128)  -- 128 维向量，最大 16383 维
);

-- 限制：不能作为主键、外键、唯一键、分区键
-- 只能用于 InnoDB 存储引擎
```

##### 移除的功能

| 移除项 | 说明 | 影响 |
|--------|------|------|
| **mysql_native_password** | 认证插件完全移除 | 旧客户端需升级 |
| **部分存储引擎** | ARCHIVE, BLACKHOLE, FEDERATED, MEMORY, MERGE | 使用这些引擎的需迁移到 InnoDB |

#### 版本选择建议

| 场景 | 推荐版本 | 原因 |
|------|----------|------|
| 新项目生产环境 | **MySQL 8.4 LTS** | 长期支持、稳定 |
| 已有 8.0 生产环境 | **MySQL 8.4 LTS** | 平滑升级、同系列 |
| 需要 VECTOR/AI 特性 | **MySQL 9.x** | 新特性支持 |
| 开发测试环境 | **MySQL 9.x** | 体验新特性 |
| 旧系统仍在 5.7 | **尽快升级到 8.4** | 5.7 已停止支持 |

### 3.2 存储引擎对比

| 特性 | InnoDB | MyISAM |
|------|--------|--------|
| 事务支持 | 完整 ACID | 不支持 |
| 锁粒度 | 行级锁 | 表级锁 |
| 外键 | 支持 | 不支持 |
| 崩溃恢复 | 自动恢复 | 需手动修复 |
| 全文索引 | 5.6+ 支持 | 支持 |
| 存储结构 | 聚簇索引 | 非聚簇索引 |
| COUNT(*) | 全表扫描 | 直接读取元数据 |
| 适用场景 | OLTP | 只读/分析 |

### 3.3 索引原理

#### B+ 树基础

MySQL InnoDB 默认使用 **B+ 树**作为索引结构：

| 特性 | 说明 |
|------|------|
| **非叶子节点** | 只存索引键（不存数据），可容纳更多索引 |
| **叶子节点** | 存储完整数据，通过**双向链表**连接 |
| **树高度** | 通常 3-4 层，1000 万数据只需 3 次 IO |
| **查询复杂度** | O(log N)，且稳定（必须到叶子节点） |

##### B+ 树结构图

```
                        ┌───────────────────┐
                        │    15  |  28      │  ← 根节点（只存索引键）
                        └───────────────────┘
                       /         |          \
            ┌─────────┐    ┌─────────┐    ┌─────────┐
            │ 5|10|12 │ ←→ │15|18|25 │ ←→ │28|30|35 │  ← 叶子节点（存数据+双向链表）
            └─────────┘    └─────────┘    └─────────┘

范围查询 WHERE id BETWEEN 10 AND 28：
1. 从根节点定位到 10 所在叶子节点
2. 沿链表遍历到 28，无需回溯
```

##### 树高与存储容量

假设：索引键 8B，指针 6B，数据行 1KB，页大小 16KB

| 树高 | 非叶子节点可存 | 总数据量 |
|------|---------------|----------|
| 2 层 | 16KB/(8+6)≈1170 | 1170 × 16 ≈ **1.8 万行** |
| 3 层 | 1170 × 1170 | 1170² × 16 ≈ **2000 万行** |
| 4 层 | 1170³ | ≈ **200 亿行** |

**结论**：3 层 B+ 树可存 2000 万数据，查询只需 3 次磁盘 IO

---

#### 三种树结构对比

##### 红黑树结构图

```
红黑树（二叉平衡树）：每个节点最多 2 个子节点

              ┌───┐
              │ 15│  (黑)
              └───┘
             /     \
        ┌───┐       ┌───┐
        │ 10│ (红)  │ 28│ (红)
        └───┘       └───┘
        /   \       /   \
     ┌───┐ ┌───┐ ┌───┐ ┌───┐
     │ 5 │ │12 │ │20 │ │35 │
     └───┘ └───┘ └───┘ └───┘

问题：1000 万数据，树高 ≈ log₂(10⁷) ≈ 24 层 = 24 次磁盘 IO！
```

##### B 树结构图

```
B 树（多路平衡树）：非叶子节点也存数据

              ┌──────────────────┐
              │ [15,data] [28,data] │  ← 非叶子节点也存数据
              └──────────────────┘
             /         |          \
    ┌────────┐   ┌────────┐   ┌────────┐
    │[5,data]│   │[18,data]│   │[30,data]│
    │[10,data]│  │[20,data]│   │[35,data]│
    └────────┘   └────────┘   └────────┘

问题：
1. 非叶子节点存数据 → 单节点能存的索引键更少 → 树更高
2. 范围查询需要中序遍历，效率低

应用：MongoDB（文档型数据库，单次查询为主）
```

##### B+ 树结构图

```
B+ 树（数据库专用）：数据只在叶子节点 + 叶子链表

              ┌───────────────┐
              │    15 | 28    │  ← 非叶子节点只存索引（更多索引=更矮的树）
              └───────────────┘
             /        |        \
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │5,10,12  │←→│15,18,25 │←→│28,30,35 │  ← 叶子节点（数据+双向链表）
    │[data...]│  │[data...]│  │[data...]│
    └─────────┘  └─────────┘  └─────────┘

优势：
1. 非叶子节点不存数据 → 单节点存更多索引 → 树更矮 → IO 更少
2. 叶子节点链表 → 范围查询只需顺序遍历

应用：MySQL InnoDB、PostgreSQL
```

##### 对比总结表

| 对比项 | 红黑树 | B 树 | B+ 树 |
|--------|--------|------|-------|
| **类型** | 二叉平衡树 | 多路平衡树 | 多路平衡树 |
| **节点存数据** | 所有节点 | 所有节点 | **仅叶子节点** |
| **叶子链表** | 无 | 无 | **有（双向）** |
| **1000万数据树高** | ~24 层 | ~4-5 层 | **~3 层** |
| **范围查询** | 中序遍历 | 中序遍历 | **链表顺序扫描** |
| **磁盘 IO** | 多 | 中 | **少** |
| **适用场景** | 内存（Java TreeMap） | MongoDB、文件系统 | **关系数据库** |

> **注**：Linux 文件系统（ext4/XFS/Btrfs）实际用的是 **B+ 树变体**，早期 ext2 类似 B 树结构。

##### 为什么 MySQL 选择 B+ 树？

| 原因 | 说明 |
|------|------|
| **磁盘 IO 是瓶颈** | 内存操作 ns 级，磁盘 IO 是 ms 级（差 10⁶ 倍） |
| **树更矮** | 非叶子节点不存数据，能存更多索引，树高仅 3-4 层 |
| **范围查询高效** | 叶子节点链表，`BETWEEN`/`ORDER BY` 只需顺序遍历 |
| **查询稳定** | 所有查询都到叶子节点，不会因数据位置不同而性能波动 |

##### 为什么不用 Hash 索引？

| 对比 | B+ 树 | Hash |
|------|-------|------|
| **等值查询** | O(log N) | O(1) |
| **范围查询** | ✅ 支持 | ❌ 不支持 |
| **排序** | ✅ 支持 | ❌ 不支持 |
| **前缀匹配** | ✅ 支持 | ❌ 不支持 |
| **适用场景** | 通用 | Memory 引擎等值查询 |

#### 聚簇索引 vs 非聚簇索引

| 类型 | 别名 | 定义 | 特点 |
|------|------|------|------|
| **聚簇索引** | 聚集索引、主键索引 | 叶子节点存储**完整行数据** | 一张表只能有一个，查询快 |
| **非聚簇索引** | 二级索引、辅助索引 | 叶子节点存储**主键值** | 可以有多个，需要回表 |

**回表**：通过二级索引找到主键，再用主键去聚簇索引查完整数据

**覆盖索引**：查询的列都在索引中，无需回表（`SELECT id, name FROM t WHERE name = 'x'`，name 索引包含 id）

---

#### 索引分类总览（按功能分类）

| 索引类型 | 数据结构 | 唯一性 | 叶子存储 | 语法 | 说明 |
|----------|----------|--------|----------|------|------|
| **主键索引** | B+树 | 唯一+非空 | 完整行数据 | `PRIMARY KEY (id)` | 聚簇索引，每表仅1个 |
| **唯一索引** | B+树 | 唯一+可空 | 主键值 | `UNIQUE INDEX (col)` | 二级索引 |
| **普通索引** | B+树 | 无约束 | 主键值 | `INDEX (col)` | 二级索引 |
| **组合索引** | B+树 | 可选唯一 | 主键值 | `INDEX (a,b,c)` | 多列拼接，最左前缀 |
| **前缀索引** | B+树 | 可选唯一 | 主键值 | `INDEX (col(N))` | 只索引前N个字符 |
| **全文索引** | **倒排索引** | - | 词→文档映射 | `FULLTEXT (content)` | 分词搜索，5.6+ |
| **空间索引** | **R树** | - | 空间数据 | `SPATIAL (geo)` | GIS场景 |

> **关于 Hash 索引**：Hash 是数据结构分类，不是功能分类。InnoDB **不支持**用户显式创建 Hash 索引，只有内部的"自适应哈希索引"（Adaptive Hash Index），由引擎自动管理。Memory 引擎支持 Hash 索引。

---

#### 索引的物理存储：多棵独立 B+ 树

**每个索引都是一棵独立的 B+ 树**。一张表有 N 个索引，就有 N 棵 B+ 树，全部存储在同一个 `.ibd` 文件中（MySQL 5.6+ 独立表空间模式）。

##### 示例

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY,              -- 索引1：聚簇索引
    email VARCHAR(100) UNIQUE,          -- 索引2：唯一索引
    name VARCHAR(50),
    age INT,
    city VARCHAR(50),
    INDEX idx_name (name),              -- 索引3：普通索引
    INDEX idx_age_city (age, city)      -- 索引4：组合索引
);
```

**这张表有 4 棵独立的 B+ 树：**

```
┌─────────────────────────────────────────────────────────────────┐
│                        users 表的 .ibd 文件                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【B+树1】聚簇索引 (PRIMARY KEY)                                 │
│  ┌─────────────────────────────────────┐                        │
│  │ 叶子节点存储: 完整行数据              │                        │
│  │ (id=1, email, name, age, city, ...) │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
│  【B+树2】唯一索引 (email)                                       │
│  ┌─────────────────────────────────────┐                        │
│  │ 叶子节点存储: (email值, 主键id)       │                        │
│  │ ("a@test.com", 1)                   │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
│  【B+树3】普通索引 (name)                                        │
│  ┌─────────────────────────────────────┐                        │
│  │ 叶子节点存储: (name值, 主键id)        │                        │
│  │ ("frank", 1)                        │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
│  【B+树4】组合索引 (age, city)                                   │
│  ┌─────────────────────────────────────┐                        │
│  │ 叶子节点存储: (age, city, 主键id)     │                        │
│  │ (25, "Beijing", 1)                  │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

##### 聚簇索引 vs 二级索引存储对比

| 索引类型 | 叶子节点存储 | 查询时 |
|----------|--------------|--------|
| 聚簇索引（主键） | **完整行数据** | 直接返回 |
| 所有二级索引（唯一/普通/组合/前缀） | **索引列值 + 主键值** | 需要**回表** |

##### 回表过程

```sql
SELECT * FROM users WHERE name = 'frank';
```

```
1. 在 name 索引的B+树中查找 'frank'
   → 找到叶子节点: (name='frank', id=1)

2. 拿到 id=1，去聚簇索引的B+树查找
   → 找到叶子节点: 完整行数据

3. 返回结果
```

##### 组合索引的排列方式

组合索引的 B+ 树按**最左列优先**排序：

```
组合索引 (a, b, c) 的排列顺序：
(1,1,1) → (1,1,2) → (1,2,1) → (2,1,1) → ...

先按 a 排序 → a 相同按 b 排序 → b 相同按 c 排序
```

这就是**最左前缀原则**的来源：只有从最左列开始的查询才能利用索引的有序性。

##### 同一字段存在于多个索引

一个字段可以同时是唯一索引，又参与组合索引，此时会形成**多棵独立的 B+ 树**，数据冗余存储。

```sql
CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    order_no VARCHAR(32),
    user_id BIGINT,
    status INT,
    UNIQUE INDEX idx_order_no (order_no),              -- 唯一索引
    INDEX idx_user_status (user_id, order_no, status)  -- 组合索引（也包含 order_no）
);
```

**`order_no` 字段在两棵 B+ 树中各存一份：**

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          orders 表的 .ibd 文件                             │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  【B+树1】聚簇索引 (id)                                                    │
│  └─ 叶子: 完整行数据                                                       │
│                                                                           │
│  【B+树2】唯一索引 idx_order_no                                            │
│  ┌─────────────────────────────────────────┐                              │
│  │ 按 order_no 排序                         │                              │
│  │ 叶子: (order_no='ORD001', id=1)         │                              │
│  │       (order_no='ORD002', id=2)         │                              │
│  └─────────────────────────────────────────┘                              │
│                                                                           │
│  【B+树3】组合索引 idx_user_status                                         │
│  ┌─────────────────────────────────────────┐                              │
│  │ 按 (user_id, order_no, status) 排序      │                              │
│  │ 叶子: (100, 'ORD001', 1, id=1)          │  ← order_no 再次存储          │
│  │       (100, 'ORD003', 2, id=3)          │                              │
│  │       (200, 'ORD002', 1, id=2)          │                              │
│  └─────────────────────────────────────────┘                              │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

**查询时使用哪个索引？由优化器根据成本估算决定：**

| 查询条件 | 使用的索引 | 原因 |
|----------|------------|------|
| `WHERE order_no = 'ORD001'` | idx_order_no | 唯一索引等值查询最精确 |
| `WHERE user_id = 100` | idx_user_status | 满足最左前缀 |
| `WHERE user_id = 100 AND order_no = 'ORD001'` | 优化器选择 | 通常选 idx_order_no（更精确） |
| `WHERE order_no = 'ORD001' AND status = 1` | idx_order_no | 组合索引不满足最左前缀 |

**设计建议**：

| 情况 | 建议 |
|------|------|
| 字段需要唯一约束 + 经常单独查询 | ✅ 保留唯一索引 |
| 组合索引主要用于其他列开头的查询 | ✅ 两个索引都保留 |
| 组合索引只是为了查这个字段 | ❌ 冗余，考虑移除 |

> **代价**：同一字段在多个索引中重复存储，增加写入开销和存储空间。

---

#### MySQL 8.0+ 索引新特性

| 特性 | 引入版本 | 说明 | 语法 |
|------|----------|------|------|
| **函数索引** | 8.0 | 对表达式建索引 | `INDEX ((YEAR(date)))` |
| **降序索引** | 8.0 | 真正降序存储，非仅语法支持 | `INDEX (col DESC)` |
| **隐藏索引** | 8.0 | 测试删除索引的影响，不实际删除 | `ALTER INDEX idx INVISIBLE` |
| **新索引默认不可见** | **9.0** | 创建索引后默认 INVISIBLE，需手动启用 | `ALTER INDEX idx VISIBLE` |

##### MySQL 9 索引行为变更

**重要变更**：MySQL 9.0 创建的新索引**默认不可见**（INVISIBLE），优化器不会使用。

```sql
-- MySQL 8.0：创建后立即生效
CREATE INDEX idx_name ON users(name);  -- 优化器立即使用

-- MySQL 9.0：创建后默认不可见
CREATE INDEX idx_name ON users(name);  -- 优化器忽略
ALTER TABLE users ALTER INDEX idx_name VISIBLE;  -- 手动启用
```

**目的**：防止新索引意外改变查询计划，导致性能回退。DBA 可以先创建索引，测试后再启用。

---

#### MySQL 8.0+ 优化器新特性（非索引）


##### 索引跳跃扫描 (Index Skip Scan)

| 项目 | 说明 |
|------|------|
| **类型** | 优化器执行策略，不是索引 |
| **引入版本** | MySQL 8.0.13+ |
| **用户能否创建** | ❌ 不能，由优化器自动决定 |
| **控制方式** | `SET optimizer_switch = 'skip_scan=on/off'` |
| **EXPLAIN 标识** | `Using index for skip scan` |

**作用**：当组合索引最左列基数很低时，即使查询不包含最左列，也能利用索引。

```sql
-- 组合索引 (gender, age)，gender 只有 '男'/'女' 两个值
-- 传统：WHERE age = 25 无法使用索引（不满足最左前缀）
-- 8.0.13+：优化器可能自动转换为跳跃扫描

EXPLAIN SELECT * FROM users WHERE age = 25;
-- Extra: Using index for skip scan
```

**触发条件**（需全部满足）：
- MySQL 8.0.13+
- 最左列基数很低（distinct 值少）
- 优化器成本估算认为跳跃扫描更优


##### 直方图 (Histogram)

| 项目 | 说明                                     |
|------|----------------------------------------|
| **类型** | 统计信息                                   |
| **引入版本** | MySQL 8.0                              |
| **用户能否创建** | ✅ **可以手动创建**                           |
| **存储位置** | `information_schema.COLUMN_STATISTICS` |
| **主要用途** | 非索引列的数据分布统计                            |

**作用**：帮助优化器更准确地估算数据分布，做出更优的执行计划。

```sql
-- 创建直方图（桶数 1-1024，官方建议从 32 开始）
ANALYZE TABLE orders UPDATE HISTOGRAM ON status WITH 32 BUCKETS;

-- 查看直方图
SELECT * FROM information_schema.COLUMN_STATISTICS
WHERE table_name = 'orders';

-- 删除直方图
ANALYZE TABLE orders DROP HISTOGRAM ON status;
```

**两种类型**：

| 类型 | 条件 | 说明 |
|------|------|------|
| **Singleton** | distinct 值 ≤ 桶数 | 一个桶存一个值 |
| **Equi-height** | distinct 值 > 桶数 | 一个桶存一个范围 |

**注意**：
- 直方图主要用于**非索引列**
- 如果有范围优化器可用，优化器**优先使用范围优化器**而非直方图
- 直方图按需创建，不会在表数据修改时自动更新


---

#### 索引失效场景

> **核心原则**：是否走索引由**优化器**决定，取决于**成本估算**。以下是常见失效场景，但 MySQL 8.0 做了很多优化。

| 场景 | 原因 | MySQL 8.0 改进 |
|------|------|----------------|
| `LIKE '%xxx'` | 前缀模糊无法利用 B+ 树有序性 | 无改进，仍不走 |
| 对索引列用函数 | `WHERE YEAR(date)=2024` 无法匹配索引值 | 支持**函数索引** |
| 隐式类型转换 | 字符串列用数字查询，触发 CAST | 无改进 |
| 最左前缀不匹配 | 组合索引 (a,b,c)，查 WHERE b=1 | 支持**索引跳跃扫描** |
| 数据量太小 | 优化器判断全表扫描更快 | 更智能的成本估算 |
| 统计信息不准 | 优化器误判 | 支持**直方图** |

##### 索引失效示例与正确写法

```sql
-- ❌ 函数导致失效
SELECT * FROM users WHERE YEAR(created_at) = 2024;
-- ✅ 改为范围查询
SELECT * FROM users WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
-- ✅ MySQL 8.0 可创建函数索引
CREATE INDEX idx_year ON users ((YEAR(created_at)));

-- ❌ 隐式类型转换（phone 是 VARCHAR）
SELECT * FROM users WHERE phone = 13800138000;
-- ✅ 使用正确类型
SELECT * FROM users WHERE phone = '13800138000';

-- ❌ LIKE 前缀模糊
SELECT * FROM users WHERE name LIKE '%frank%';
-- ✅ 考虑全文索引或搜索引擎（ES）

-- ❌ OR 连接非索引列
SELECT * FROM users WHERE name = 'frank' OR age = 30;
-- ✅ 给 age 加索引，或拆分为 UNION
```

### 3.4 日志系统

#### 三大核心日志对比

| 对比项 | binlog | redo log | undo log |
|--------|--------|----------|----------|
| **层级** | Server 层 | InnoDB 引擎层 | InnoDB 引擎层 |
| **作用** | 主从复制、数据恢复 | 崩溃恢复（保证持久性） | 事务回滚、MVCC |
| **内容** | 逻辑日志（SQL 或行变更） | 物理日志（页的修改） | 逻辑日志（反向操作） |
| **写入时机** | 事务提交时 | 事务执行中 | 事务执行中 |
| **文件** | binlog.00000x | ib_logfile0/1（循环写） | 共享表空间/undo 表空间 |
| **是否必需** | 可关闭 | 不可关闭 | 不可关闭 |

#### 其他日志

| 日志 | 作用 | 默认状态 |
|------|------|----------|
| slow query log | 慢查询分析优化 | 关闭 |
| error log | 错误诊断 | 开启 |
| general log | 全量 SQL 记录（调试用） | 关闭 |
| relay log | 从库复制中继 | 主从架构开启 |

#### Binlog 详解

##### 三种格式对比

| 格式 | 记录内容 | 优点 | 缺点 | 场景 |
|------|----------|------|------|------|
| **STATEMENT** | 原始 SQL | 日志量小 | NOW()/UUID() 等不确定函数复制不准 | 已不推荐 |
| **ROW** | 行数据变更 | 复制精确、可用于数据恢复 | 日志量大（批量更新） | **推荐（默认）** |
| **MIXED** | 自动选择 | 兼顾两者 | 复杂度高 | 特殊场景 |

##### sync_binlog 参数

| 值 | 行为 | 性能 | 安全性 |
|----|------|------|--------|
| **0** | 由 OS 决定何时刷盘 | 最高 | 最低（OS 崩溃丢数据） |
| **1** | 每次提交刷盘 | 最低 | **最高（推荐）** |
| **N** | 每 N 次事务刷盘 | 折中 | 可能丢 N-1 个事务 |

#### Redo Log 详解

##### 为什么需要 redo log？

- **问题**：数据页 16KB，磁盘扇区 512B，写数据页可能只写了一部分就崩溃（部分写失效）
- **解决**：先写 redo log（顺序 IO、小量数据），崩溃后重放 redo log 恢复数据

##### innodb_flush_log_at_trx_commit

| 值 | 行为 | 数据安全 | 性能 |
|----|------|----------|------|
| **0** | 每秒刷盘 | 可能丢 1 秒数据 | 最高 |
| **1** | 每次提交刷盘 | **最安全（ACID 保证）** | 最低 |
| **2** | 提交写 OS 缓存 | OS 崩溃丢数据 | 中等 |

##### Redo Log 循环写入

```
┌────────────────────────────────────────┐
│  ib_logfile0  │  ib_logfile1  │ ...   │
│  [write_pos]→ │               │       │
│               │  ←[checkpoint]│       │
└────────────────────────────────────────┘
- write_pos: 当前写入位置（追赶 checkpoint）
- checkpoint: 已刷盘数据位置
- 当 write_pos 追上 checkpoint，需要等待刷脏页
```

#### Undo Log 详解

##### 作用

| 功能 | 说明 |
|------|------|
| **事务回滚** | 记录反向操作（INSERT→DELETE，UPDATE→旧值） |
| **MVCC** | 提供历史版本，实现快照读 |

##### 类型

- **insert undo log**：INSERT 产生，事务提交后可立即删除
- **update undo log**：UPDATE/DELETE 产生，需要保留到没有快照读使用

#### 两阶段提交

**问题**：binlog 和 redo log 是两个独立的日志，如何保证一致性？

**解决**：内部 XA 事务（两阶段提交）

```
┌─────────────────────────────────────────────────────┐
│ 1. Prepare 阶段                                      │
│    - 写 redo log，状态设为 prepare                    │
│    - 写 binlog                                       │
│                                                     │
│ 2. Commit 阶段                                       │
│    - redo log 状态改为 commit                        │
└─────────────────────────────────────────────────────┘

崩溃恢复策略：
- redo log 有 prepare，binlog 完整 → 提交
- redo log 有 prepare，binlog 不完整 → 回滚
- redo log 已 commit → 提交
```

##### 为什么先写 redo log 再写 binlog？

| 顺序 | 崩溃场景 | 结果 |
|------|----------|------|
| 先 binlog | binlog 写完崩溃 | 从库有数据，主库没有 → **主从不一致** |
| 先 redo log (prepare) | prepare 后崩溃 | 检查 binlog → 一致性恢复 |

#### WAL (Write-Ahead Logging) 机制

**核心原则**：先写日志，再写数据页

##### 完整事务提交流程

```
1. 开始事务
2. 读取数据页到 Buffer Pool（如不在内存）
3. 写 undo log（用于回滚和 MVCC）
4. 修改 Buffer Pool 中的数据页（脏页）
5. 写 redo log 到 Log Buffer
6. 【Prepare】redo log 刷盘，状态=prepare
7. 写 binlog 到 binlog cache
8. binlog 刷盘
9. 【Commit】redo log 状态改为 commit
10. 返回客户端提交成功
11. 后台线程异步将脏页刷到磁盘（Checkpoint）
```

##### 为什么用 WAL？

| 方面 | 直接写数据页 | WAL |
|------|-------------|-----|
| **IO 类型** | 随机 IO | 顺序 IO |
| **写入量** | 整页 16KB | 只写变更部分 |
| **性能** | 慢 | 快几个数量级 |
| **崩溃恢复** | 数据丢失 | 重放日志恢复 |


### 3.5 MVCC (多版本并发控制)

#### 核心原理

MVCC 通过保存数据的历史版本，实现**读不加锁，读写不冲突**：

- **DB_TRX_ID**：最后修改该行的事务 ID
- **DB_ROLL_PTR**：指向 undo log 中的上一版本
- **Read View**：快照读时生成，记录活跃事务列表

```
版本链示例：
当前版本 (trx_id=103) --> undo log (trx_id=102) --> undo log (trx_id=100)
```

#### 可见性判断

```
Read View 包含：
- min_trx_id: 创建时最小活跃事务 ID
- max_trx_id: 创建时应该分配给下一个事务的 ID
- m_ids: 创建时的活跃事务 ID 列表

判断规则：
1. trx_id < min_trx_id → 可见（事务已提交）
2. trx_id >= max_trx_id → 不可见（事务在快照后开启）
3. min_trx_id <= trx_id < max_trx_id → 检查是否在 m_ids 中
   - 不在 m_ids 中 → 可见（事务已提交）
   - 在 m_ids 中 → 不可见（事务仍活跃）
```

#### 隔离级别与 MVCC

| 隔离级别 | Read View 生成时机 | 问题 |
|----------|-------------------|------|
| READ UNCOMMITTED | 不使用 MVCC | 脏读 |
| READ COMMITTED | 每次 SELECT 生成新的 | 不可重复读 |
| REPEATABLE READ | 事务首次 SELECT 生成 | 幻读（InnoDB 通过间隙锁解决） |
| SERIALIZABLE | 加锁，不用 MVCC | 性能差 |

```go
// Go 中设置隔离级别
tx, err := db.BeginTx(ctx, &sql.TxOptions{
    Isolation: sql.LevelRepeatableRead,
    ReadOnly:  false,
})
```

### 3.6 锁机制

#### 锁粒度

| 锁类型 | 触发条件 | 特点 |
|--------|----------|------|
| **表锁** | 无索引的条件查询 | 粒度大，并发差 |
| **行锁** | 有索引且命中的条件查询 | 粒度小，并发好 |

#### 行锁类型

| 类型 | 说明 | 触发条件 |
|------|------|----------|
| **记录锁** | 锁定单行记录 | 唯一索引等值查询且记录存在 |
| **间隙锁** | 锁定索引间隙 | 唯一索引等值查询且记录不存在 |
| **临键锁** | 记录锁 + 间隙锁 | 范围查询 |

```sql
-- 记录锁：锁定 id=1 的行
SELECT * FROM users WHERE id = 1 FOR UPDATE;

-- 间隙锁：id=5 不存在，锁定 (3, 7) 区间
SELECT * FROM users WHERE id = 5 FOR UPDATE;

-- 临键锁：锁定 (10, 20] 区间
SELECT * FROM users WHERE id > 10 AND id <= 20 FOR UPDATE;
```

#### 共享锁 vs 排他锁

```sql
-- 共享锁 (S锁)：允许其他事务读，不允许写
SELECT * FROM users WHERE id = 1 LOCK IN SHARE MODE;  -- MySQL 5.7
SELECT * FROM users WHERE id = 1 FOR SHARE;           -- MySQL 8.0+

-- 排他锁 (X锁)：不允许其他事务读写
SELECT * FROM users WHERE id = 1 FOR UPDATE;
```

```go
// Go 中使用 FOR UPDATE
func lockUser(tx *sql.Tx, userID int64) (*User, error) {
    var user User
    err := tx.QueryRow("SELECT id, name, balance FROM users WHERE id = ? FOR UPDATE", userID).
        Scan(&user.ID, &user.Name, &user.Balance)
    return &user, err
}
```

#### 死锁处理

```go
// 方法 1：设置锁超时
// my.cnf: innodb_lock_wait_timeout = 50

// 方法 2：固定加锁顺序
func transfer(db *sql.DB, fromID, toID int64, amount float64) error {
    // 始终按 ID 升序加锁，避免死锁
    if fromID > toID {
        fromID, toID = toID, fromID
        amount = -amount
    }
    // ...
}

// 方法 3：捕获死锁重试
func executeWithRetry(db *sql.DB, fn func(*sql.Tx) error) error {
    for i := 0; i < 3; i++ {
        tx, _ := db.Begin()
        err := fn(tx)
        if err != nil {
            tx.Rollback()
            if isDeadlock(err) {
                time.Sleep(time.Duration(i*100) * time.Millisecond)
                continue
            }
            return err
        }
        return tx.Commit()
    }
    return errors.New("max retry exceeded")
}

func isDeadlock(err error) bool {
    // MySQL 死锁错误码: 1213
    var mysqlErr *mysql.MySQLError
    if errors.As(err, &mysqlErr) {
        return mysqlErr.Number == 1213
    }
    return false
}
```

### 3.7 ACID 特性

| 特性 | 实现机制 |
|------|----------|
| **原子性 (Atomicity)** | undo log |
| **一致性 (Consistency)** | redo log + undo log + 锁 |
| **隔离性 (Isolation)** | MVCC + 锁 |
| **持久性 (Durability)** | redo log |

### 3.8 意向锁 (Intention Locks)

意向锁用于协调行锁和表锁，支持多粒度锁共存。

| 类型 | 说明 | 作用 |
|------|------|------|
| **IS (意向共享锁)** | 事务计划对某些行加 S 锁 | 阻止其他事务对整表加 X 锁 |
| **IX (意向排他锁)** | 事务计划对某些行加 X 锁 | 阻止其他事务对整表加 S/X 锁 |

```sql
-- 当执行行级锁时，MySQL 自动在表级加意向锁
SELECT * FROM users WHERE id = 1 FOR UPDATE;
-- 实际加锁：表级 IX 锁 + 行级 X 锁

-- 意向锁兼容矩阵
--        IS    IX    S     X
-- IS     ✓     ✓     ✓     ✗
-- IX     ✓     ✓     ✗     ✗
-- S      ✓     ✗     ✓     ✗
-- X      ✗     ✗     ✗     ✗
```

### 3.9 Online DDL

修改表结构时不锁表的机制（MySQL 5.6+）。

#### 执行算法

| 算法 | 说明 | 是否锁表 |
|------|------|----------|
| **COPY** | 创建临时表，复制数据 | 锁表（禁止 DML） |
| **INPLACE** | 原地修改，分 rebuild 和 no-rebuild | 基本不锁表 |

```sql
-- 指定算法和锁级别
ALTER TABLE users ADD INDEX idx_name (name), ALGORITHM=INPLACE, LOCK=NONE;

-- LOCK 选项：
-- NONE: 允许并发 DML
-- SHARED: 允许读，禁止写
-- EXCLUSIVE: 禁止读写
-- DEFAULT: MySQL 自动选择
```

#### Online DDL 支持情况

| 操作 | 算法 | 是否重建表 |
|------|------|------------|
| 添加索引 | INPLACE | 否 |
| 删除索引 | INPLACE | 否 |
| 添加列 | INPLACE | 是 |
| 删除列 | INPLACE | 是 |
| 修改列类型 | COPY | 是 |
| 添加主键 | INPLACE | 是 |

#### 执行过程

```
1. Prepare 阶段
   - 创建临时 frm 文件
   - 加独占 MDL 锁（短暂）
   - 确定算法

2. DDL 执行阶段
   - 降级为共享 MDL 锁，允许 DML
   - 扫描原表，复制到新表（rebuild 时）
   - 增量修改记录到 row log

3. Commit 阶段
   - 升级为独占 MDL 锁（短暂）
   - 应用 row log 中的增量
   - 替换表定义，完成
```

### 3.10 数据同步与 CDC

#### Binlog 复制架构

```
主库 (Master)
    │
    ├── binlog ──────────────────┐
    │                            │
    ▼                            ▼
从库1 (Slave)               从库2 (Slave)
    │                            │
    └── relay log                └── relay log
```

#### CDC (Change Data Capture) 方案

| 方案 | 原理 | 适用场景 |
|------|------|----------|
| **Canal** | 模拟 MySQL Slave，解析 binlog | 阿里开源，Java 生态 |
| **Debezium** | 基于 Kafka Connect | 多数据源，云原生 |
| **Flink CDC** | 基于 Debezium | 实时计算场景 |
| **go-mysql** | Go 实现的 binlog 解析 | Go 生态 |

#### Go 中使用 go-mysql 监听 binlog

```go
import "github.com/go-mysql-org/go-mysql/replication"

func syncBinlog() {
    cfg := replication.BinlogSyncerConfig{
        ServerID: 100,
        Flavor:   "mysql",
        Host:     "127.0.0.1",
        Port:     3306,
        User:     "root",
        Password: "password",
    }

    syncer := replication.NewBinlogSyncer(cfg)
    streamer, _ := syncer.StartSync(mysql.Position{Name: "mysql-bin.000001", Pos: 4})

    for {
        ev, _ := streamer.GetEvent(context.Background())
        switch e := ev.Event.(type) {
        case *replication.RowsEvent:
            // 处理行变更
            fmt.Printf("Table: %s, Action: %s\n", e.Table.Table, ev.Header.EventType)
            for _, row := range e.Rows {
                fmt.Printf("Row: %v\n", row)
            }
        }
    }
}
```

---

## 第四部分：性能优化

### 4.1 服务器参数优化

#### 内存相关参数

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `innodb_buffer_pool_size` | InnoDB 缓冲池大小 | 物理内存的 60-80% |
| `innodb_buffer_pool_instances` | 缓冲池实例数 | 8（大内存时） |
| `sort_buffer_size` | 排序缓冲区 | 256KB-2MB |
| `join_buffer_size` | JOIN 缓冲区 | 256KB-1MB |
| `tmp_table_size` | 内存临时表大小 | 64MB-256MB |
| `max_heap_table_size` | 用户创建的内存表大小 | 与 tmp_table_size 相同 |

#### IO 相关参数

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `innodb_io_capacity` | IO 能力（IOPS） | SSD: 2000-20000, HDD: 200 |
| `innodb_read_io_threads` | 读 IO 线程数 | 4-8 |
| `innodb_write_io_threads` | 写 IO 线程数 | 4-8 |
| `innodb_flush_log_at_trx_commit` | redo log 刷盘策略 | 1（安全）或 2（性能） |
| `sync_binlog` | binlog 刷盘策略 | 1（安全）或 0/N（性能） |

#### 连接相关参数

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `max_connections` | 最大连接数 | 根据业务，通常 200-1000 |
| `table_open_cache` | 表缓存数 | 2000-4000 |
| `thread_cache_size` | 线程缓存数 | 50-100 |

```sql
-- 查看缓冲池命中率
SHOW STATUS LIKE 'Innodb_buffer_pool_read%';
-- 命中率 = 1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)
-- 建议 > 99%

-- 查看临时表使用情况
SHOW STATUS LIKE 'Created_tmp%';
-- 如果 Created_tmp_disk_tables 过高，增加 tmp_table_size
```

### 4.2 查询优化

#### EXPLAIN 分析

```sql
EXPLAIN SELECT * FROM users WHERE name = 'frank';
```

| 列 | 含义 | 关注点 |
|----|------|--------|
| type | 访问类型 | const > eq_ref > ref > range > index > ALL |
| key | 实际使用的索引 | NULL 表示未使用索引 |
| rows | 预估扫描行数 | 越小越好 |
| Extra | 额外信息 | Using filesort, Using temporary 需优化 |

#### 常见优化手段

```sql
-- 1. 避免 SELECT *
SELECT id, name FROM users WHERE id = 1;

-- 2. 使用覆盖索引
-- 索引: (name, age)
SELECT name, age FROM users WHERE name = 'frank';  -- 无需回表

-- 3. 分页优化
-- 低效：
SELECT * FROM users ORDER BY id LIMIT 1000000, 10;
-- 高效（延迟关联）：
SELECT * FROM users u
JOIN (SELECT id FROM users ORDER BY id LIMIT 1000000, 10) t
ON u.id = t.id;

-- 4. JOIN 优化
-- 小表驱动大表
SELECT * FROM small_table s
JOIN large_table l ON s.id = l.sid;

-- 5. 避免子查询，改用 JOIN
-- 低效：
SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE status = 1);
-- 高效：
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.status = 1;
```

### 4.2 Go 应用层优化

#### 连接池调优

```go
// 根据业务并发量设置
sqlDB.SetMaxOpenConns(runtime.NumCPU() * 10) // 经验值
sqlDB.SetMaxIdleConns(runtime.NumCPU() * 2)
sqlDB.SetConnMaxLifetime(time.Hour)
sqlDB.SetConnMaxIdleTime(10 * time.Minute)

// 监控连接池状态
go func() {
    for {
        stats := sqlDB.Stats()
        log.Printf("Open: %d, InUse: %d, Idle: %d, WaitCount: %d",
            stats.OpenConnections, stats.InUse, stats.Idle, stats.WaitCount)
        time.Sleep(time.Minute)
    }
}()
```

#### 预编译语句

```go
// 对于频繁执行的 SQL，使用预编译提升性能
stmt, err := db.Prepare("SELECT id, name FROM users WHERE id = ?")
if err != nil {
    log.Fatal(err)
}
defer stmt.Close()

for _, id := range userIDs {
    var user User
    err := stmt.QueryRow(id).Scan(&user.ID, &user.Name)
    // ...
}
```

#### Context 超时控制

```go
func queryWithTimeout(db *sql.DB, userID int64) (*User, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()

    var user User
    err := db.QueryRowContext(ctx, "SELECT id, name FROM users WHERE id = ?", userID).
        Scan(&user.ID, &user.Name)

    if errors.Is(err, context.DeadlineExceeded) {
        return nil, errors.New("query timeout")
    }
    return &user, err
}
```

### 4.3 写入优化

#### 批量插入对比

| 方式 | 性能 | 适用场景 |
|------|------|----------|
| 单条 INSERT | 最慢 | 少量数据 |
| 批量 VALUES | 较快 | 中等数据量 |
| LOAD DATA | 最快 | 大批量导入 |
| 事务批量提交 | 较快 | 需要控制逻辑 |

```go
// 事务批量提交
func batchInsertWithTx(db *sql.DB, users []User) error {
    tx, err := db.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()

    stmt, err := tx.Prepare("INSERT INTO users (name, age) VALUES (?, ?)")
    if err != nil {
        return err
    }
    defer stmt.Close()

    for _, u := range users {
        if _, err := stmt.Exec(u.Name, u.Age); err != nil {
            return err
        }
    }

    return tx.Commit()
}
```

### 4.4 架构优化

#### 读写分离

```go
type DBCluster struct {
    Master *sql.DB
    Slaves []*sql.DB
    idx    uint64
}

func (c *DBCluster) Write() *sql.DB {
    return c.Master
}

func (c *DBCluster) Read() *sql.DB {
    // 轮询选择从库
    idx := atomic.AddUint64(&c.idx, 1)
    return c.Slaves[idx%uint64(len(c.Slaves))]
}

// 使用
func getUser(cluster *DBCluster, id int64) (*User, error) {
    var user User
    err := cluster.Read().QueryRow("SELECT * FROM users WHERE id = ?", id).
        Scan(&user.ID, &user.Name)
    return &user, err
}

func createUser(cluster *DBCluster, user *User) error {
    _, err := cluster.Write().Exec("INSERT INTO users (name) VALUES (?)", user.Name)
    return err
}
```

#### 分库分表

**水平拆分（分表）**：同结构的数据按规则分散到多张表
- 按时间：`orders_202401`, `orders_202402`
- 按 ID 取模：`users_0`, `users_1`, ..., `users_15`
- 按地区：`users_cn`, `users_us`

**垂直拆分（分库）**：不同业务的数据分到不同库
- 用户库：user_db
- 订单库：order_db
- 商品库：product_db

**难点**：
- 分布式事务
- 跨库 JOIN
- 全局唯一 ID（雪花算法、UUID）
- 数据迁移

Go 语言分库分表方案：

| 方案 | 类型 | 说明 | GitHub |
|------|------|------|--------|
| **gorm/sharding** | Go 客户端库 | GORM 官方分片插件，支持雪花 ID | gorm.io/sharding |
| **kingshard** | Go 代理层 | 国产高性能 MySQL 代理，支持读写分离、分片 | github.com/flike/kingshard |
| **Vitess** | Go 代理层 | YouTube 开源，K8s 原生，大规模分片 | vitess.io |
| **TiDB** | NewSQL | 兼容 MySQL 协议，自动分片，免中间件 | pingcap.com |

> **推荐**：小规模用 gorm/sharding 或应用层分片；大规模用 Vitess 或直接上 TiDB。

应用层分片示例：

```go
func getShardDB(userID int64, dbs []*sql.DB) *sql.DB {
    shardIndex := userID % int64(len(dbs))
    return dbs[shardIndex]
}

func getTableName(userID int64) string {
    return fmt.Sprintf("users_%d", userID%16) // 16 张分表
}

func getUser(dbs []*sql.DB, userID int64) (*User, error) {
    db := getShardDB(userID, dbs)
    table := getTableName(userID)

    query := fmt.Sprintf("SELECT id, name FROM %s WHERE id = ?", table)
    var user User
    err := db.QueryRow(query, userID).Scan(&user.ID, &user.Name)
    return &user, err
}
```

### 4.6 高可用架构

#### 主从复制

```
         ┌─────────────┐
         │   Master    │  ← 写入
         │  (Active)   │
         └──────┬──────┘
                │ binlog
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌───────┐  ┌───────┐  ┌───────┐
│ Slave │  │ Slave │  │ Slave │  ← 读取
└───────┘  └───────┘  └───────┘
```

#### 主从 + 读写分离

```go
// 使用 go-mysql-proxy 或自建代理
type MySQLCluster struct {
    Master   *sql.DB
    Slaves   []*sql.DB
    slaveIdx uint64
}

func (c *MySQLCluster) WriteDB() *sql.DB {
    return c.Master
}

func (c *MySQLCluster) ReadDB() *sql.DB {
    idx := atomic.AddUint64(&c.slaveIdx, 1)
    return c.Slaves[idx%uint64(len(c.Slaves))]
}
```

#### 高可用方案对比

| 方案 | 特点 | 适用场景 |
|------|------|----------|
| **MHA** | 主库故障自动切换 | 传统主从架构 |
| **MGR** | MySQL 官方组复制 | MySQL 8.0+ |
| **Galera** | 多主同步复制 | 写入量不大的场景 |
| **Orchestrator** | 自动拓扑管理 | 复杂主从拓扑 |

### 4.7 缓存策略

#### 多级缓存架构

```
请求 → 本地缓存 → Redis → MySQL
         ↓           ↓        ↓
      命中率高    命中率中   最终数据源
```

```go
import (
    "github.com/patrickmn/go-cache"
    "github.com/redis/go-redis/v9"
)

type CacheService struct {
    localCache *cache.Cache     // 本地缓存
    redis      *redis.Client    // Redis
    db         *sql.DB          // MySQL
}

func (s *CacheService) GetUser(ctx context.Context, id int64) (*User, error) {
    key := fmt.Sprintf("user:%d", id)

    // 1. 本地缓存
    if v, ok := s.localCache.Get(key); ok {
        return v.(*User), nil
    }

    // 2. Redis
    data, err := s.redis.Get(ctx, key).Bytes()
    if err == nil {
        var user User
        json.Unmarshal(data, &user)
        s.localCache.Set(key, &user, 5*time.Minute) // 回填本地缓存
        return &user, nil
    }

    // 3. MySQL
    user, err := s.getUserFromDB(id)
    if err != nil {
        return nil, err
    }

    // 回填缓存
    data, _ = json.Marshal(user)
    s.redis.Set(ctx, key, data, 30*time.Minute)
    s.localCache.Set(key, user, 5*time.Minute)

    return user, nil
}
```

#### 缓存更新策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **Cache Aside** | 先更新 DB，再删除缓存 | 通用方案 |
| **Read/Write Through** | 缓存层代理读写 | 缓存一致性要求高 |
| **Write Behind** | 异步批量写 DB | 写入量大 |

---

## 第五部分：最佳实践

### 5.1 表设计规范

```sql
-- 推荐表结构
CREATE TABLE users (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    name        VARCHAR(100) NOT NULL DEFAULT '' COMMENT '姓名',
    email       VARCHAR(200) NOT NULL DEFAULT '' COMMENT '邮箱',
    status      TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态: 0-正常 1-禁用',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted_at  DATETIME DEFAULT NULL COMMENT '删除时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_email (email),
    KEY idx_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

设计要点：
- **主键**：使用 BIGINT UNSIGNED AUTO_INCREMENT
- **字符集**：统一使用 utf8mb4
- **NOT NULL**：尽量避免 NULL，使用默认值
- **时间字段**：使用 DATETIME 或 TIMESTAMP，配合 DEFAULT 和 ON UPDATE
- **注释**：必须添加 COMMENT

### 5.2 Go 代码规范

```go
// 1. 结构体定义
type User struct {
    ID        int64      `db:"id" json:"id"`
    Name      string     `db:"name" json:"name"`
    Email     string     `db:"email" json:"email"`
    Status    int8       `db:"status" json:"status"`
    CreatedAt time.Time  `db:"created_at" json:"created_at"`
    UpdatedAt time.Time  `db:"updated_at" json:"updated_at"`
    DeletedAt *time.Time `db:"deleted_at" json:"deleted_at,omitempty"`
}

// 2. 错误处理
func GetUser(db *sql.DB, id int64) (*User, error) {
    var user User
    err := db.QueryRow("SELECT id, name FROM users WHERE id = ?", id).
        Scan(&user.ID, &user.Name)

    switch {
    case errors.Is(err, sql.ErrNoRows):
        return nil, ErrUserNotFound
    case err != nil:
        return nil, fmt.Errorf("query user %d: %w", id, err)
    }
    return &user, nil
}

// 3. 资源释放
func ListUsers(db *sql.DB) ([]User, error) {
    rows, err := db.Query("SELECT id, name FROM users")
    if err != nil {
        return nil, err
    }
    defer rows.Close() // 必须关闭

    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name); err != nil {
            return nil, err
        }
        users = append(users, u)
    }

    if err := rows.Err(); err != nil { // 检查迭代错误
        return nil, err
    }
    return users, nil
}
```

### 5.3 监控指标

```go
import "github.com/prometheus/client_golang/prometheus"

var (
    dbQueryDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "db_query_duration_seconds",
            Help:    "Database query duration",
            Buckets: []float64{.001, .005, .01, .05, .1, .5, 1},
        },
        []string{"query"},
    )

    dbErrors = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "db_errors_total",
            Help: "Database error count",
        },
        []string{"type"},
    )
)

func queryWithMetrics(db *sql.DB, query string, args ...interface{}) (*sql.Rows, error) {
    start := time.Now()
    rows, err := db.Query(query, args...)

    dbQueryDuration.WithLabelValues(query).Observe(time.Since(start).Seconds())
    if err != nil {
        dbErrors.WithLabelValues("query").Inc()
    }

    return rows, err
}
```

### 5.4 常见问题排查

| 问题 | 排查方法 |
|------|----------|
| 连接耗尽 | 检查 `db.Stats()`，确认连接池配置 |
| 查询慢 | EXPLAIN 分析，检查索引 |
| 死锁 | 查看 `SHOW ENGINE INNODB STATUS` |
| 主从延迟 | `SHOW SLAVE STATUS` 查看 Seconds_Behind_Master |
| 锁等待 | `SELECT * FROM information_schema.INNODB_LOCK_WAITS` |

---

## 附录：Go MySQL 生态

### 驱动与增强

| 库 | 用途 | GitHub |
|----|------|--------|
| go-sql-driver/mysql | MySQL 驱动（必装） | github.com/go-sql-driver/mysql |
| sqlx | database/sql 增强，结构体映射 | github.com/jmoiron/sqlx |

### ORM 框架

| 库 | 用途 | GitHub |
|----|------|--------|
| GORM | 最流行的 ORM，功能全面 | gorm.io/gorm |
| ent | Facebook 开源，代码生成型 ORM | entgo.io/ent |
| sqlc | **SQL→Go 代码生成器**（写SQL自动生成类型安全Go函数） | github.com/sqlc-dev/sqlc |

### 分库分表与代理

| 库 | 用途 | GitHub |
|----|------|--------|
| gorm/sharding | GORM 分片插件 | gorm.io/sharding |
| kingshard | Go 实现的 MySQL 代理，读写分离+分片 | github.com/flike/kingshard |
| go-mysql | binlog 解析、复制协议实现 | github.com/go-mysql-org/go-mysql |

### 数据库迁移

| 库 | 用途 | GitHub |
|----|------|--------|
| goose | 轻量迁移工具，支持 SQL 和 Go | github.com/pressly/goose |
| golang-migrate | 通用迁移工具，多数据库支持 | github.com/golang-migrate/migrate |
| atlas | 声明式 Schema 管理 | atlasgo.io |