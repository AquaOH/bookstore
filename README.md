**华东师范大学数据科学与工程学院实验报告** 

| **课程名称：当代数据管理系统** | **指导教师：周烜**    | **上机实践名称：** **Bookstore** |
| ------------------------------ | --------------------- | -------------------------------- |
| **姓名**：邓博昊               | **学号**：10225501432 | **年级：2022**                   |

# 1.实验要求

## 功能

- **1人**完成下述内容：
  1. 允许向接口中增加或修改参数，允许修改 HTTP 方法，允许增加新的测试接口，请尽量不要修改现有接口的 url 或删除现有接口，请根据设计合理的拓展接口（加分项+2～5分）。 测试程序如果有问题可以提bug （加分项，每提1个 bug +2, 提1个 pull request +5）。
  2. 核心数据使用关系型数据库（PostgreSQL 或 MySQL 数据库）。 blob 数据（如图片和大段的文字描述）可以分离出来存其它 NoSQL 数据库或文件系统。
  3. 对所有的接口都要写 test case，通过测试并计算代码覆盖率（有较高的覆盖率是加分项 +2~5）。
  4. 尽量使用正确的软件工程方法及工具，如，版本控制，测试驱动开发 （利用版本控制是加分项 +2~5）
  5. 后端使用技术，实现语言不限；**不要复制**这个项目上的后端代码（不是正确的实践， 减分项 -2~5）
  6. 不需要实现页面
  7. 最后评估分数时考虑以下要素：
     1）实现完整度，全部测试通过，效率合理
     2）正确地使用数据库和设计分析工具，ER图，从ER图导出关系模式，规范化，事务处理，索引等
     3）其它...

## bookstore目录结构

```text
bookstore
  |-- be                            后端
        |-- model                     后端逻辑代码
        |-- view                      访问后端接口
        |-- ....
  |-- doc                           JSON API规范说明
  |-- fe                            前端访问与测试代码
        |-- access
        |-- bench                     效率测试
        |-- data                    
            |-- book.db                 
            |-- scraper.py              从豆瓣爬取的图书信息数据的代码
        |-- test                      功能性测试（包含对前60%功能的测试，不要修改已有的文件，可以提pull request或bug）
        |-- conf.py                   测试参数，修改这个文件以适应自己的需要
        |-- conftest.py               pytest初始化配置，修改这个文件以适应自己的需要
        |-- ....
  |-- ....
```

# 2.MongoDB向Postgres迁移

原项目为Homework1，其使用的核心数据库为`MongoDB`,现将其迁移到`Postgres`上

只需要改变后端`model`即可，其余可不变

# 3.前期分析与数据库设计与前期分析

### 3.1 数据库设计

#### 3.1.1 数据库逻辑设计

![5902e98de450373369ea44427a6799b](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/5902e98de450373369ea44427a6799b.png)

#### 3.1.2 数据库结构设计

**表：`user`**

| 字段名     | 数据类型  | 约束 | 说明         |
| ---------- | --------- | ---- | ------------ |
| `user_id`  | `TEXT`    | 主键 | 用户ID       |
| `password` | `TEXT`    | 非空 | 用户密码     |
| `balance`  | `NUMERIC` | 非空 | 用户余额     |
| `token`    | `TEXT`    |      | 用户登录令牌 |
| `terminal` | `TEXT`    |      | 用户终端信息 |

**表：`book`**

| 字段名           | 数据类型  | 约束 | 说明             |
| ---------------- | --------- | ---- | ---------------- |
| `id`             | `SERIAL`  | 主键 | 自增ID           |
| `book_id`        | `TEXT`    | 非空 | 书籍ID           |
| `title`          | `TEXT`    | 非空 | 书名             |
| `author`         | `TEXT`    |      | 作者             |
| `publisher`      | `TEXT`    |      | 出版社           |
| `content`        | `TEXT`    |      | 内容             |
| `original_title` | `TEXT`    |      | 原书名           |
| `translator`     | `TEXT`    |      | 译者             |
| `pub_year`       | `TEXT`    |      | 出版年份         |
| `pages`          | `INTEGER` |      | 页数             |
| `price`          | `INTEGER` |      | 价格             |
| `currency_unit`  | `TEXT`    |      | 货币单位         |
| `binding`        | `TEXT`    |      | 装帧             |
| `isbn`           | `TEXT`    |      | ISBN号           |
| `author_intro`   | `TEXT`    |      | 作者简介         |
| `book_intro`     | `TEXT`    |      | 书籍简介         |
| `tags`           | `JSONB`   |      | 标签（JSON数组） |
| `pictures`       | `JSONB`   |      | 图片（JSON数组） |

**表：`store`**

| 字段名     | 数据类型 | 约束             | 说明              |
| ---------- | -------- | ---------------- | ----------------- |
| `store_id` | `TEXT`   | 主键             | 商店ID            |
| `user_id`  | `TEXT`   | 外键（`user`表） | 用户ID            |
| `books`    | `JSONB`  |                  | 书籍信息（JSONB） |

**表：`order`**

| 字段名        | 数据类型    | 约束         | 说明         |
| ------------- | ----------- | ------------ | ------------ |
| `id`          | `SERIAL`    | 主键         | 自增ID       |
| `order_id`    | `TEXT`      |              | 订单ID       |
| `store_id`    | `TEXT`      |              | 商店ID       |
| `user_id`     | `TEXT`      |              | 用户ID       |
| `create_time` | `TIMESTAMP` | 默认当前时间 | 订单创建时间 |
| `price`       | `NUMERIC`   | 非空         | 订单总价     |
| `status`      | `TEXT`      | 非空         | 订单状态     |

**表：`order_detail`**

| 字段名     | 数据类型  | 约束 | 说明     |
| ---------- | --------- | ---- | -------- |
| `id`       | `SERIAL`  | 主键 | 自增ID   |
| `order_id` | `TEXT`    |      | 订单ID   |
| `book_id`  | `TEXT`    |      | 书籍ID   |
| `price`    | `NUMERIC` | 非空 | 书籍单价 |
| `count`    | `INTEGER` | 非空 | 书籍数   |



#### 3.1.3索引优化

为了对数据库进行优化，可以对那些不怎么更改，但是需要经常查找的项建立索引，有了索引的存在就可以加快查找速度，所以设置了以下索引。

* **store 表中的 `store_id` 上设置了唯一升序索引**：
  - `store_id` 是商店的唯一标识符，经常用于查询商店信息。通过在该字段上创建唯一升序索引，可以快速定位到特定的商店记

* **user 表中的 `user_id` 上设置了唯一升序索引**：
  - `user_id` 是用户的唯一标识符，经常用于用户登录、查询用户信息等操作。通过在该字段上创建唯一升序索引，可以快速定位到特定用户记录，提升查询效率。

* **books 表中设置了多个索引**：

  - **`title` 字段上的普通索引**：`title` 是书籍的标题，经常用于根据书名进行搜索。通过在 `title` 上创建普通索引，可以加快基于书名的查询速度。
  - **`tags` 字段上的 GIN 索引**：`tags` 是一个 JSONB 类型的字段，存储书籍的标签信息。

  - **`book_intro` 字段上的 GIN 索引**：`book_intro` 是书籍的简介，通常包含较长的文本信息。

### 3.2 前期分析

#### 3.2.1 文件树分析

```cmd
(.venv) ~\Desktop\大三上\当代数据管理系统\Homework\大作业\CDMS.Xuan_ZHOU.2024Fall.DaSE\project1\bookstore git:[dev-dbh]
tree /A
Folder PATH listing for volume Win11ProW X64
Volume serial number is 16B4-98DD
C:.
+---be	# 后端文件夹，处理实际的业务逻辑
|   +---model	# 数据模型，主要为实际运行时的内部逻辑与sqlite数据库读写，需要重构为操作Mongodb
|   |   \---__pycache__
|   +---view	# flask的后端逻辑
|   |   \---__pycache__
|   \---__pycache__
+---doc
+---fe	# 前端文件夹，主要存放测试和调用后端相关函数(模拟浏览器行为)
|   +---access	# 规定了前端如何调用后端，基本上不需要改动了
|   |   \---__pycache__
|   +---bench	# 测试打分相关
|   |   \---__pycache__
|   +---data	# 存放的sqlite数据，需要后面转到Mongodb上
|   +---test	# 用于pytest框架的测试函数
|   |   \---__pycache__
|   \---__pycache__
\---script	# 存放测试脚本
```

#### 3.2.2 业务逻辑分析

一次测试中标准的业务流程如下

1. 搜索测试文件
   - Flask 框架
     - 搜索当前文件树下的测试文件
       - 规则：
         - 以 `test_` 开头
         - 以 `_test` 结尾
       - 包含特定目录中的测试：
         - `/fe/bench`

2. 测试文件执行逻辑
   - 测试文件调用
     - `/fe/access` 中的前端逻辑
     - 前端执行逻辑：
       - 向后端发送 HTTP 指令

3. 后端逻辑
   - 接收前端 HTTP 指令
     - 后端通过 `/be/view` 中的函数解析 HTTP 参数
     - 执行解析包含的指令

4. 后端调用
   - `/be/model` 中的对应函数

#### 3.2.3 对比分析

PostgresSQL和MongoDB对比



1. MongoDB URI

   ```
   mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
   ```

2. 术语对比

   | MySQL 术语          | MongoDB 术语                                                 | 解释                                                         |
   | ------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
   | Database（数据库）  | Database（数据库）                                           | 两者中都使用相同术语，表示数据库的集合。                     |
   | Table（表）         | Collection（集合）                                           | 在MySQL中称为表，在MongoDB中称为集合，存储数据记录的容器。   |
   | Row（行）           | Document（文档）                                             | 在MySQL中每行代表一条记录，而在MongoDB中每个文档是类似的概念，包含数据的键值对。 |
   | Column（列）        | Field（字段）                                                | MySQL的列对应MongoDB的字段，字段表示文档中键值对的键。       |
   | Primary Key（主键） | `_id`（唯一标识符）                                          | MySQL中的主键在MongoDB中对应每个文档的`_id`字段，默认由MongoDB生成唯一ID。 |
   | Index（索引）       | Index（索引）                                                | 两者都用索引来加速查询，但MongoDB的索引可以是嵌套的字段或数组。 |
   | Schema（模式）      | Schema-less（无模式）                                        | MySQL有固定模式，MongoDB是无模式的，即文档的结构不必一致。   |
   | JOIN（连接）        | Embedded Documents（嵌入文档） 或 `$lookup`                  | MongoDB没有直接的JOIN，但可以通过嵌入文档或`$lookup`操作实现类似的功能。 |
   | SQL（查询语言）     | MongoDB Query（MongoDB查询）或 Aggregation Pipeline（聚合管道） | MySQL使用SQL语言，MongoDB有自己的查询语法和聚合框架。        |
   | Transaction（事务） | Transaction（事务）                                          | MongoDB 4.0+版本支持多文档ACID事务，类似MySQL的事务。        |
   | Foreign Key（外键） | Reference（引用）                                            | MongoDB没有明确的外键概念，但可以通过引用文档的方式实现类似的功能。 |
   | View（视图）        | View（视图）                                                 | MongoDB 3.4+版本支持视图，与MySQL的视图类似。                |

#### 3.2.4 初次运行

请将Flask降级到2.0.0



将`~/script/test.sh`改成`test.bat`

运行提示，请在项目根目录下运行

```bat
@echo off
setlocal

echo 设置当前目录为 PYTHONPATH
set PYTHONPATH=%cd%

echo 运行 coverage，并指定路径和参数
coverage run --timid --branch --source=fe,be --concurrency=thread -m pytest -v --ignore=fe\data

echo 合并覆盖率数据
coverage combine

echo 生成覆盖率报告
coverage report

echo 生成 HTML 覆盖率报告
coverage html

endlocal

```

然后运行

可以看到`./be/model/user.py`中的`jwt_encode`出了问题

![image-20241012110839105](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241012110839105.png)

查看`jwt_encode`

```py
def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.decode("utf-8")
```

查询网络后发现，在 `pyjwt` 的较早版本中，`jwt.encode` 返回的是字节对象，需要通过 `.decode("utf-8")` 将其转换为字符串。

从2.0版本开始，`jwt.encode` 直接返回字符串，因此不再需要进行解码。

只需要将 `jwt_encode` 函数中的 `.decode("utf-8")` 移除。修改后的函数如下：

```python
def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded  # 不再需要 decode
```

可以看到上述问题已解决



![image-20241012111337535](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241012111337535.png)



同时整体修改思路如下(仅基础功能)

* 前端`fe`不需要更改，其模拟的是浏览器行为，存放设计好的测试函数
* 后端`be/view`不需要更改，其为后端`Flask`处理HTTP请求并调用处理核心`be/model`部分
* 后端`be/model/error.py`不需要更改，预先设计好的错误代码
* 其余`be/model/`下的文件需要更改

# 4.基本功能实现

从上次的实验一代码，将MongoDB为核心改为以Postgres为核心

### 4.1 buyer部分实现

#### 4.1.1 new_order

**函数输入**：

- `user_id`：字符串，表示用户的唯一标识。
- `store_id`：字符串，表示商店的唯一标识。
- `id_and_count`：列表，包含多个元组，每个元组由书本的 ID 和其对应的数量组成。

**函数输出**：

- 整数：状态码，200 表示操作成功，528 表示错误。
- 字符串：描述操作结果的消息，可能是成功或错误信息。
- 字符串：表示订单的 ID。

**函数流程**：

1. 初始化一个空字符串 `order_id`，用于后续存储订单 ID。
2. 检查用户和商店的存在性。如果任一不存在，函数将返回相应的错误消息和空的订单 ID。
3. 生成一个唯一的订单 ID `uid`，该 ID 由用户 ID、商店 ID 及一个基于当前时间的唯一标识符组成。
4. 遍历 `id_and_count` 列表中的每个书本 ID 及其数量，执行以下操作：
   - 查询商店的库存，确认书本的存在性。如果书本未找到，将返回相应的错误信息和空的订单 ID。
   - 检查库存量，若库存不足，返回库存不足的错误信息和空的订单 ID。
   - 如果库存充足，更新库存，减少相应书本的数量。
   - 将书本的订单详细信息记录到 `order_detail` 表中，并计算订单的总价。
5. 在计算完总价格后，函数获取当前时间，将订单的详细信息插入到 `order` 表中，包括订单 ID、商店 ID、用户 ID、创建时间、总价格及订单状态。
6. 如果所有步骤均成功，函数返回状态码 200 表示成功以及生成的订单 ID。
7. 如果在执行过程中捕获到异常，会记录相关日志，并返回 528 表示错误，同时附带异常信息作为错误消息，并返回空的订单 ID。



#### 4.1.2 payment

**函数输入**：

- `user_id`：用户标识。
- `password`：用户密码。
- `order_id`：订单唯一标识。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：操作结果的描述。

**函数流程**：

1. 查询 `order` 表中与给定订单 ID 对应的订单信息，状态为 0（未付款）。如果未找到有效的订单，将返回一个错误消息，提示无效的订单 ID。
2. 如果找到订单信息，则提取买家的 ID、商店 ID 和订单的总价。
3. 验证用户 ID 是否与订单的买家 ID 一致，如果不匹配，返回授权失败的错误消息。
4. 查询 `user` 表中买家的信息，确认用户存在并核对密码。如果出现错误，返回授权失败的消息。
5. 查询 `store` 表中商店信息，确保商店存在。如果找不到，将返回相应的错误消息。
6. 从商店信息中提取卖家的 ID，检查卖家是否存在。如果未找到，返回错误消息。
7. 检查用户余额，如果余额不足，返回余额不足的错误消息。
8. 如果余额充足，从买家的账户中扣除订单总价，并将该金额添加到卖家的账户中。
9. 更新 `order` 表中订单状态为 1（已支付）。
10. 如果执行过程中发生任何异常，返回状态码 528。

#### 4.1.3 add_funds

**函数输入**：

- `user_id`：用户标识。
- `password`：用户密码。
- `add_value`：增加到账户余额的金额。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 查询 `user` 表中与给定用户 ID 对应的用户信息。如果未找到，返回授权失败的错误消息。
2. 如果找到信息，验证输入的密码是否与数据库中的密码一致。如果不匹配，返回授权失败的错误提示。
3. 更新 `user` 表中用户的余额，将 `add_value` 添加到当前余额。
4. 如果更新失败，返回用户不存在的错误消息。
5. 如果在执行过程中发生任何异常，返回状态码 528。



#### 4.1.4 改动的理由：

* **便于编写业务逻辑代码**：
  - PostgreSQL 支持复杂的 SQL 查询和事务处理，能够简化业务逻辑代码的编写。

* **数据一致性**：
  - PostgreSQL 的 ACID 事务能够确保数据的一致性，避免数据不一致的问题。

* **扩展性**：
  - PostgreSQL 支持多种数据类型和扩展，能够满足复杂的业务需求。

### 4.2 seller部分实现

#### 4.2.1 创建商铺

**函数输入**：

- `user_id`：卖家用户 ID。
- `store_id`：商铺 ID。

**函数输出**：

- 整数：状态码，200 表示成功，530 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 检查给定的 `user_id` 是否存在。如果不存在，返回一个错误，表示用户 ID 不存在。
2. 检查给定的 `store_id` 是否存在。如果存在，返回一个错误，表示商店 ID 已存在。
3. 使用 `INSERT INTO` 语句向 `store` 表中插入新商店。商店的基本信息包括：
   - `store_id`：新商店的唯一标识符。
   - `user_id`：关联的用户 ID。
   - `books`：初始化为空的 JSONB 数组，表示该商店当前没有任何书籍。
4. 如果在执行数据库操作时发生异常，返回错误代码 530 和错误信息。
5. 如果所有操作成功完成，返回状态码 200 和消息 `"ok"`，表示操作成功。

#### 4.2.2 添加书籍信息

**函数输入**：

- `user_id`：卖家用户 ID。
- `store_id`：商铺 ID。
- `book_id`：书籍 ID。
- `book_json_str`：表示包含书籍信息的 JSON 字符串。
- `stock_level`：库存数量。

**函数输出**：

- 整数：状态码，200 表示成功，530 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 检查给定的 `user_id` 是否存在。如果不存在，返回一个错误，表示用户 ID 不存在。
2. 检查给定的 `store_id` 是否存在。如果不存在，返回一个错误，表示商店 ID 不存在。
3. 检查给定的 `book_id` 是否已存在于商店中。如果存在，返回一个错误，表示书籍 ID 已存在。
4. 解析书籍信息的 JSON 字符串，并将其插入到 `book` 表中。
5. 使用 `jsonb_insert` 函数将书籍 ID 和库存数量添加到商店的 `books` 字段中。
6. 如果在执行数据库操作时发生异常，返回错误代码 530 和错误信息。
7. 如果所有操作成功完成，返回状态码 200 和消息 `"ok"`，表示操作成功。

#### 4.2.3 添加书籍库存

**函数输入**：

- `user_id`：卖家用户 ID。
- `store_id`：商铺 ID。
- `book_id`：书籍 ID。
- `add_stock_level`：增加的库存数量。

**函数输出**：

- 整数：状态码，200 表示成功，528 或 530 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 检查给定的 `user_id` 是否存在。如果不存在，返回一个错误，表示用户 ID 不存在。
2. 检查给定的 `store_id` 是否存在。如果不存在，返回一个错误，表示商店 ID 不存在。
3. 检查给定的 `book_id` 是否存在于商店中。如果不存在，返回一个错误，表示书籍 ID 不存在。
4. 使用 `jsonb_set` 函数更新商店中指定书籍的库存数量。
5. 如果在执行数据库操作时发生 `psycopg2.Error` 异常，返回错误代码 528 和错误信息。如果发生其他类型的异常，返回错误代码 530 和错误信息。
6. 如果所有操作成功完成，返回状态码 200 和消息 `"ok"`，表示操作成功。

### 4.3 user部分实现

#### 4.3.1 注册

**函数输入**：

- `user_id`：用户 ID。
- `password`：用户密码。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 生成一个唯一的终端标识，格式为 `terminal_<当前时间戳>`。
2. 使用 `jwt_encode` 函数生成一个 JWT Token。
3. 将用户信息插入到 `user` 表中，包括 `user_id`、`password`、`balance`、`token` 和 `terminal`。
4. 如果在执行数据库操作时发生异常，返回错误代码 528 和错误信息。
5. 如果操作成功，返回状态码 200 和消息 `"ok"`。

#### 4.3.2 登录

**函数输入**：

- `user_id`：用户 ID。
- `password`：用户密码。
- `terminal`：用户终端信息。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：描述操作结果的消息。
- 字符串：生成的 JWT Token。

**函数流程**：

1. 调用 `check_password` 函数验证用户提供的密码是否正确。
2. 如果密码验证失败，返回相应的错误代码和消息。
3. 使用 `jwt_encode` 函数生成一个新的 JWT Token。
4. 更新 `user` 表中的 `token` 和 `terminal` 字段。
5. 如果在执行数据库操作时发生异常，返回错误代码 528 和错误信息。
6. 如果操作成功，返回状态码 200、消息 `"ok"` 以及生成的 Token。

#### 4.3.3 登出

**函数输入**：

- `user_id`：用户 ID。
- `token`：用户提供的 Token。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 调用 `check_token` 函数验证用户提供的 Token 是否有效。
2. 如果 Token 验证失败，返回相应的错误代码和消息。
3. 生成一个新的虚拟终端标识和 Token。
4. 更新 `user` 表中的 `token` 和 `terminal` 字段。
5. 如果在执行数据库操作时发生异常，返回错误代码 528 和错误信息。
6. 如果操作成功，返回状态码 200 和消息 `"ok"`。

#### 4.3.4 注销

**函数输入**：

- `user_id`：用户 ID。
- `password`：用户密码。

**函数输出**：

- 整数：状态码，200 表示成功，530 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 调用 `check_password` 函数验证用户提供的密码是否正确。
2. 如果密码验证失败，返回相应的错误代码和消息。
3. 从 `user` 表中删除用户记录。
4. 如果在执行数据库操作时发生异常，返回错误代码 530 和错误信息。
5. 如果操作成功，返回状态码 200 和消息 `"ok"`。

#### 4.3.5 改密

**函数输入**：

- `user_id`：用户 ID。
- `old_password`：旧密码。
- `new_password`：新密码。

**函数输出**：

- 整数：状态码，200 表示成功，528 表示发生错误。
- 字符串：描述操作结果的消息。

**函数流程**：

1. 调用 `check_password` 函数验证用户提供的旧密码是否正确。
2. 如果旧密码验证失败，返回相应的错误代码和消息。
3. 生成一个新的终端标识和 Token。
4. 更新 `user` 表中的 `password`、`token` 和 `terminal` 字段。
5. 如果在执行数据库操作时发生异常，返回错误代码 528 和错误信息。
6. 如果操作成功，返回状态码 200 和消息 `"ok"`。

#### 修改后端`model/store.py`

原有`store.py`关联的是SQLite数据库

##### 被调用链

1. `be/model/`中的类初始化时

​	调用`db_conn.DBConn`的初始化函数

![image-20241026222717814](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241026222717814.png)

2. `be/model/db_conn.DBConn`初始化时

   调用`store.get_db_conn()`函数

3. `store.get_db_conn()`调用`database_instance.get_db_conn()`函数
   `database_instance`为`Store`类的一个实例

   

![image-20241026223137663](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241026223137663.png)

##### 修改方向

1. 全部改为self.xxx，作为类的属性，方便调用
2. 删除database: str，因为不再是SQLite,显然返回的类型应该为`Map`类型
3. `get_db_conn(self)`返回类自己即可
4. 删除`db_path`
5. `init_database`在`serve.py`里被调用，原来参数为父文件夹目录，现在无参数输入，数据库初始化在`Store()`类里完成
   ![image-20241226133207428](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241226133207428.png)
6. 创建关于图书标题，标签，简洁，内容的索引

```python
import logging
import psycopg2
import psycopg2.extras
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Store:
    def __init__(self):
        """
        初始化 Store 类，连接 PostgreSQL 数据库并初始化数据表。
        """
        # 初始化数据库连接
        self.conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            user="postgres",
            password=os.getenv("DB_PASSWORD", "Aqua7296"),
            database="bookstore"
        )
        # 初始化数据表
        self.init_tables()

    def init_tables(self):
        """
        初始化数据库表结构，包括 user、book、store、order 和 order_detail 表。
        如果表已存在，则先删除再重新创建。
        """
        try:
            with self.conn.cursor() as cursor:
                # 删除并重新创建 user 表
                cursor.execute('DROP TABLE IF EXISTS "user";')
                cursor.execute("""
                    CREATE TABLE "user" (
                        user_id TEXT PRIMARY KEY,  -- 用户ID为主键
                        password TEXT NOT NULL,   -- 用户密码
                        balance NUMERIC NOT NULL, -- 用户余额
                        token TEXT,               -- 用户登录令牌
                        terminal TEXT             -- 用户终端信息
                    );
                """)

                # 在 user_id 上创建唯一升序索引（主键已自动创建索引）
                cursor.execute('CREATE UNIQUE INDEX idx_user_id ON "user" (user_id);')

                # 删除并重新创建 book 表
                cursor.execute('DROP TABLE IF EXISTS "book";')
                cursor.execute("""
                    CREATE TABLE "book" (
                        id SERIAL PRIMARY KEY,
                        book_id TEXT NOT NULL,    -- 书籍ID
                        title TEXT NOT NULL,             -- 书名
                        author TEXT,                     -- 作者
                        publisher TEXT,                  -- 出版社
                        content TEXT,                    -- 内容
                        original_title TEXT,             -- 原书名
                        translator TEXT,                 -- 译者
                        pub_year TEXT,                   -- 出版年份
                        pages INTEGER,                   -- 页数
                        price INTEGER,                   -- 价格
                        currency_unit TEXT,              -- 货币单位
                        binding TEXT,                    -- 装帧
                        isbn TEXT,                -- ISBN号
                        author_intro TEXT,               -- 作者简介
                        book_intro TEXT,                 -- 书籍简介
                        tags JSONB,                      -- 标签（JSON数组）
                        pictures JSONB                   -- 图片链接（JSON数组）
                    );
                """)

                # 在 title 上创建普通索引
                cursor.execute('CREATE INDEX idx_title ON "book" (title);')

                # 在 tags 上创建 GIN 索引
                cursor.execute('CREATE INDEX idx_tags ON "book" USING GIN (tags);')

                # 在 book_intro 上创建 GIN 索引，支持全文搜索
                cursor.execute("""
                    CREATE INDEX idx_book_intro ON "book" USING GIN (to_tsvector('english', book_intro));
                """)

                # 在 content 上创建 GIN 索引，支持全文搜索
                cursor.execute("""
                    CREATE INDEX idx_content ON "book" USING GIN (to_tsvector('english', content));
                """)

                # 删除并重新创建 store 表
                cursor.execute('DROP TABLE IF EXISTS "store";')
                cursor.execute("""
                    CREATE TABLE "store" (
                        store_id TEXT PRIMARY KEY,  -- 商店ID为主键
                        user_id TEXT REFERENCES "user"(user_id), -- 用户ID，外键
                        books JSONB                 -- 书籍信息，使用 JSONB 类型存储
                    );
                """)

                # 在 store_id 上创建唯一升序索引（主键已自动创建索引）
                cursor.execute('CREATE UNIQUE INDEX idx_store_id ON "store" (store_id);')

                # 删除并重新创建 order 表
                cursor.execute('DROP TABLE IF EXISTS "order";')
                cursor.execute("""
                    CREATE TABLE "order" (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT,  
                        store_id TEXT,
                        user_id TEXT,
                        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 订单创建时间
                        price NUMERIC NOT NULL,    -- 订单总价
                        status TEXT NOT NULL     -- 订单状态
                    );
                """)

                # 删除并重新创建 order_detail 表
                cursor.execute('DROP TABLE IF EXISTS "order_detail";')
                cursor.execute("""
                    CREATE TABLE "order_detail" (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT,
                        book_id TEXT,
                        price NUMERIC NOT NULL,    -- 书籍单价
                        count INTEGER NOT NULL     -- 书籍数量
                    );
                """)

                # 提交事务
                self.conn.commit()
        except psycopg2.Error as e:
            # 捕获数据库错误并记录日志
            logging.error(e)
            # 回滚事务
            self.conn.rollback()

    def get_db_conn(self):
        """
        获取数据库连接对象。

        :return: 数据库连接对象
        """
        return self.conn

    def close(self):
        """
        关闭数据库连接。
        """
        if self.conn:
            self.conn.close()


# 全局变量，用于存储数据库实例
database_instance: Store = None
# 全局变量，用于数据库初始化的同步
init_completed_event = threading.Event()


def init_database():
    """
    初始化数据库实例。
    """
    global database_instance
    if database_instance is None:
        # 初始化数据库实例
        database_instance = Store()


def get_db_conn():
    """
    获取数据库连接对象。如果数据库实例未初始化，则先初始化。

    :return: 数据库连接对象
    """
    global database_instance
    if database_instance is None:
        init_database()
    return database_instance.get_db_conn()
```

#### 再次运行

注意将`fe/conf.py`里的`Use_Large_DB = True`改为False

因为是本地测试，还未用助教所提的超大数据库

运行结果如下

![image-20241027025601617](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241027025601617.png)

# 5.附加功能

### 5.1收货发货

#### 5.1.1发货

函数输入：

user_id：卖家用户ID

order_id：订单ID

函数功能解释：

1.使用 `$or` 操作符查找具有指定 `order_id` 并且状态为 `1`、`2` 或 `3` 的订单。`find_one` 方法用于查找符合条件的第一条记录，并将结果存储在 `result` 变量中。

2.如果查询结果为 `None`，表示没有找到符合条件的订单，函数会返回一个错误，表示示订单 ID 无效。

3.从查询结果中获取订单的状态。如果状态为 `2`（已交付）或 `3`（已完成），则返回一个错误，指示该订单已经被交付或完成，不能重复交付。

4.如果订单状态有效且可以交付，则使用 `update_one` 方法将订单的状态更新为 `2`（表示已交付）。

5.如果在执行数据库操作时发生 `sqlite.Error` 异常，返回错误代码 `528` 和错误信息。如果发生其他类型的异常，返回错误代码 `530` 和错误信息。

6.如果所有操作成功完成，返回状态码 `200` 和消息 `"ok"`，表示操作成功。

#### 5.1.2收货

函数输入：

user_id：卖家用户ID

store_id：商铺ID

book_id：书籍ID 

add_stock_level：增加的库存量

函数功能解释：

1.使用 `$or` 操作符查找具有指定 `order_id` 并且状态为 `1`、`2` 或 `3` 的订单。`find_one` 方法用于查找符合条件的第一条记录，并将结果存储在 `result` 变量中。

2.如果查询结果为 `None`，表示没有找到符合条件的订单，函数会返回一个错误，表示示订单 ID 无效。

3.从查询结果中提取买家的用户 ID 和订单状态。

4.检查请求的用户 ID 是否与订单的买家 ID 匹配。如果不匹配，返回授权失败的错误信息。

5.如果订单状态为 1，表示书籍尚未发货，返回相应的错误信息。如果订单状态为 3，表示书籍已经被重复接收，返回相应的错误信息。

6.如果以上检查都通过，更新订单状态为 3（已接收）。

7.如果在执行数据库操作时发生 `sqlite.Error` 异常，返回错误代码 `528` 和错误信息。如果发生其他类型的异常，返回错误代码 `530` 和错误信息。

8.如果所有操作成功完成，返回状态码 `200` 和消息 `"ok"`，表示操作成功。

#### 5.1.3发货测试

1.test_ok 发货成功

操作：卖家发货。 

预期结果：发货成功，返回码为200。 

2.test_order_error 订单不存在

操作：使用不存在的订单ID尝试发货。 

预期结果：发货失败，返回码不为200。 

3.test_books_repeat_deliver 重复发货

操作：卖家发货两次。 

预期结果：第一次发货成功，第二次发货失败，返回码不为200。

#### 5.1.4收货测试

1.test_ok 收货成功

操作：卖家发货，买家收货。 

预期结果：收货成功，返回码为200。 

2.test_order_error  订单不存在 

操作：卖家发货，使用不存在的订单ID尝试收货。 

预期结果：收货失败，返回码不为200。 

3.test_authorization_error 买家不存在 

操作：卖家发货，使用不存在的买家ID尝试收货。 

预期结果：收货失败，返回码不为200。

4.test_books_not_deliver  未发货 

操作：未发货的订单尝试收货。 

预期结果：收货失败，返回码不为200。 

5.test_books_repeat_receive 重复收货 

操作：卖家发货，买家收货两次。 

预期结果：第一次收货成功，第二次收货失败，返回码不为200。

#### 5.1.5前后端接口

be/view/seller.py

be/view/buyer.py

fe/access/seller.py

fe/access/buyer.py

这个几个文件都新增一个函数，就照着之前的写，改几个变量就好了。

#### 5.1.6error

新增三个对应发货和收获的错误

```
520: "books not deliver.",
521: "books deliver repeatedly.",
522: "books receive repeatedly.",
```

### 5.2搜索图书

#### 5.2.1 搜索功能概述

根据前文业务流程分析依次需要实现的

* 添加`fe/test/search.py`
* 添加`fe/access/search.py`
* 添加`be/view/search.py`(记得在serve.py里注册蓝图)
* 添加`be/model/book.py`



实现了以下搜索功能：

1. **搜索指定标题的图书**：根据书名搜索书籍，支持分页和指定商店。
2. **搜索指定标签的图书**：根据标签搜索书籍，支持分页和指定商店。
3. **搜索指定内容的图书**：根据书籍简介或内容进行全文搜索，支持分页和指定商店。
4. **搜索指定作者的图书**：根据作者搜索书籍，支持分页和指定商店。

这些功能通过 `be/model/book.py` 中的方法实现，并通过 `be/view/search.py` 提供 HTTP 接口。

---

#### 5.2.2 搜索指定标题的图书

**函数输入**：

- `title`：要搜索的书名。
- `store_id`：商店 ID，如果为空字符串，则搜索所有商店。
- `page_num`：页码，从 1 开始。
- `page_size`：每页显示的书籍数量。

**函数输出**：

- 整数：状态码，200 表示成功，501 表示未找到书籍，530 表示发生错误。
- 字符串：描述操作结果的消息。
- 列表：包含搜索到的书籍信息。

**函数流程**：

1. 使用 `SELECT` 语句查询 `book` 表中标题等于 `title` 的书籍，并按 `id` 排序，支持分页。
2. 如果指定了 `store_id`，则进一步过滤出该商店中的书籍。
3. 如果未找到书籍，返回状态码 501 和错误信息。
4. 如果找到书籍，返回状态码 200、消息 `"ok"` 以及书籍列表。

**代码实现**：

```python
def search_title_in_store(self, title: str, store_id: str, page_num: int, page_size: int):
    try:
        with self.conn.cursor() as cursor:
            # 查询书籍信息
            cursor.execute("""
                SELECT * FROM book
                WHERE title = %s
                ORDER BY id
                LIMIT %s OFFSET %s;
            """, (title, page_size, (page_num - 1) * page_size))
            result_list = cursor.fetchall()

            # 如果指定了 store_id，过滤出该商店中的书籍
            if store_id:
                books_in_store = []
                for book in result_list:
                    cursor.execute("""
                        SELECT 1 FROM store
                        WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                    """, (store_id, book['book_id']))
                    if cursor.fetchone():
                        books_in_store.append(book)
                result_list = books_in_store

            if not result_list:
                return 501, f"{title} book not exist", []
            return 200, "ok", result_list

    except Exception as e:
        logging.error(str(e))
        self.conn.rollback()
        return 530, "{}".format(str(e)), []

def search_title(self, title: str, page_num: int, page_size: int):
    return self.search_title_in_store(title, "", page_num, page_size)
```

---

#### 5.2.3 搜索指定标签的图书

**函数输入**：

- `tag`：要搜索的标签。
- `store_id`：商店 ID，如果为空字符串，则搜索所有商店。
- `page_num`：页码，从 1 开始。
- `page_size`：每页显示的书籍数量。

**函数输出**：

- 整数：状态码，200 表示成功，501 表示未找到书籍，530 表示发生错误。
- 字符串：描述操作结果的消息。
- 列表：包含搜索到的书籍信息。

**函数流程**：

1. 使用 `SELECT` 语句查询 `book` 表中 `tags` 字段包含指定标签的书籍，并按 `id` 排序，支持分页。
2. 如果指定了 `store_id`，则进一步过滤出该商店中的书籍。
3. 如果未找到书籍，返回状态码 501 和错误信息。
4. 如果找到书籍，返回状态码 200、消息 `"ok"` 以及书籍列表。

**代码实现**：

```python
def search_tag_in_store(self, tag: str, store_id: str, page_num: int, page_size: int):
    try:
        with self.conn.cursor() as cursor:
            # 查询书籍信息
            cursor.execute("""
                SELECT * FROM book
                WHERE tags @> %s
                ORDER BY id
                LIMIT %s OFFSET %s;
            """, (json.dumps([tag]), page_size, (page_num - 1) * page_size))
            result_list = cursor.fetchall()

            # 如果指定了 store_id，过滤出该商店中的书籍
            if store_id:
                books_in_store = []
                for book in result_list:
                    cursor.execute("""
                        SELECT 1 FROM store
                        WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                    """, (store_id, book['book_id']))
                    if cursor.fetchone():
                        books_in_store.append(book)
                result_list = books_in_store

            if not result_list:
                return 501, f"{tag} book not exist", []
            return 200, "ok", result_list

    except Exception as e:
        logging.error(str(e))
        self.conn.rollback()
        return 530, "{}".format(str(e)), []

def search_tag(self, tag: str, page_num: int, page_size: int):
    return self.search_tag_in_store(tag, "", page_num, page_size)
```

---

#### 5.2.4 搜索指定内容的图书

**函数输入**：

- `content`：要搜索的内容。
- `store_id`：商店 ID，如果为空字符串，则搜索所有商店。
- `page_num`：页码，从 1 开始。
- `page_size`：每页显示的书籍数量。

**函数输出**：

- 整数：状态码，200 表示成功，501 表示未找到书籍，530 表示发生错误。
- 字符串：描述操作结果的消息。
- 列表：包含搜索到的书籍信息。

**函数流程**：

1. 使用 `to_tsvector` 和 `to_tsquery` 进行全文搜索，查询 `book` 表中 `book_intro` 或 `content` 字段包含指定内容的书籍，支持分页。
2. 如果指定了 `store_id`，则进一步过滤出该商店中的书籍。
3. 如果未找到书籍，返回状态码 501 和错误信息。
4. 如果找到书籍，返回状态码 200、消息 `"ok"` 以及书籍列表。

**代码实现**：

```python
def search_content_in_store(self, content: str, store_id: str, page_num: int, page_size: int):
    cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 全文搜索查询（同时匹配 book_intro 和 content 字段）
    query = """
    SELECT * FROM book
    WHERE to_tsvector('english', book_intro || ' ' || content) @@ to_tsquery('english', %s)
    OFFSET %s LIMIT %s
    """
    content_query = " & ".join(content.split())  # 预处理 content
    logging.info(
        f"Executing full-text search query: {query} with params: {content_query}, {(page_num - 1) * page_size}, {page_size}")
    cursor.execute(query, (content_query, (page_num - 1) * page_size, page_size))
    result_list = cursor.fetchall()
    logging.info(f"Full-text search result: {result_list}")

    if store_id:
        # 查询指定商店中的书籍
        store_query = """
        SELECT store_id
        FROM store
        WHERE store_id = %s AND EXISTS (
            SELECT 1
            FROM jsonb_array_elements(books) AS book
            WHERE book->>'book_id' = %s
        )
        """
        books_in_store = []
        for book in result_list:
            logging.info(f"Checking if book {book['book_id']} exists in store {store_id}")
            cursor.execute(store_query, (store_id, book["book_id"]))
            store_result = cursor.fetchone()
            logging.info(f"Store query result for book {book['book_id']}: {store_result}")
            if store_result:  # 判断查询结果是否为空
                books_in_store.append(book)
        result_list = books_in_store

    if len(result_list) == 0:
        logging.warning(f"No books found for content: {content} in store: {store_id}")
        return 501, f"{content} book not exist", []
    return 200, "ok", result_list

def search_content(self, content: str, page_num: int, page_size: int):
    return self.search_content_in_store(content, "", page_num, page_size)
```

---

#### 5.2.5 搜索指定作者的图书

**函数输入**：

- `author`：要搜索的作者。
- `store_id`：商店 ID，如果为空字符串，则搜索所有商店。
- `page_num`：页码，从 1 开始。
- `page_size`：每页显示的书籍数量。

**函数输出**：

- 整数：状态码，200 表示成功，501 表示未找到书籍，530 表示发生错误。
- 字符串：描述操作结果的消息。
- 列表：包含搜索到的书籍信息。

**函数流程**：

1. 使用 `SELECT` 语句查询 `book` 表中作者等于 `author` 的书籍，并按 `id` 排序，支持分页。
2. 如果指定了 `store_id`，则进一步过滤出该商店中的书籍。
3. 如果未找到书籍，返回状态码 501 和错误信息。
4. 如果找到书籍，返回状态码 200、消息 `"ok"` 以及书籍列表。

**代码实现**：

```python
def search_author_in_store(self, author: str, store_id: str, page_num: int, page_size: int):
    try:
        with self.conn.cursor() as cursor:
            # 查询书籍信息
            cursor.execute("""
                SELECT * FROM book
                WHERE author = %s
                ORDER BY id
                LIMIT %s OFFSET %s;
            """, (author, page_size, (page_num - 1) * page_size))
            result_list = cursor.fetchall()

            # 如果指定了 store_id，过滤出该商店中的书籍
            if store_id:
                books_in_store = []
                for book in result_list:
                    cursor.execute("""
                        SELECT 1 FROM store
                        WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                    """, (store_id, book['book_id']))
                    if cursor.fetchone():
                        books_in_store.append(book)
                result_list = books_in_store

            if not result_list:
                return 501, f"{author} book not exist", []
            return 200, "ok", result_list

    except Exception as e:
        logging.error(str(e))
        self.conn.rollback()
        return 530, "{}".format(str(e)), []

def search_author(self, author: str, page_num: int, page_size: int):
    return self.search_author_in_store(author, "", page_num, page_size)
```

### 5.3 订单状态以及查询

#### 5.3.1 check_hist_order

函数输入：

- `user_id`：用户标识

函数输出：

在内部创建一个包含历史订单信息的列表 `ans`，并在最后返回该列表

函数流程：

1. 检查用户是否存在。如果用户不存在，将返回一个错误消息，提示无效的用户ID
2. 如果存在，初始化一个空列表 `ans`，用于存储历史订单
3. 查询不同状态的订单，依次处理：
   - 查找未付款的订单，并将这些订单的信息添加到 `ans` 列表
   - 查找已支付但尚未发货、已支付但未收到和已收到的订单，并将相关信息也添加到 `ans` 列表
   - 查找已取消的订单，并将这些信息加入 `ans` 列表
4. 对于每种订单状态，执行以下操作：
   - 查询与用户ID和相应订单状态匹配的订单信息
   - 针对每个订单，获取与其相关的书籍详细信息
   - 为每个订单创建一个字典，包含状态、订单ID、买家ID、商店ID、总价及书籍详细信息，并将该字典添加到 `ans` 列表中
5. 在处理完所有状态后，检查 ans列表：
   - 如果列表为空，返回一条成功消息，指示没有找到任何历史订单
   - 如果列表非空，返回成功消息，并附上包含历史订单信息的 `ans` 列表
6. 如果在以上过程中发生任何异常，函数将捕获并返回状态码528

#### 5.3.2 cancel_order

函数输入：

- `user_id`：用户标识
- `order_id`：订单标识

函数输出：

- 一个整数：状态码，200表示成功，528表示发生错误
- 一个字符串：描述操作结果的消息

函数流程：

1. 函数在订单集合中查找状态为0的订单，使用给定的订单ID，如果找到匹配的订单，提取买家ID、商店ID和订单价格，然后从订单集合中删除该订单
2. 如果未能找到未付款的订单，函数将使用 $or操作符查找状态为1、2或3的订单。如果找到相应订单，提取买家ID、商店ID和订单价格，并执行以下操作：
   - 验证买家ID是否与输入的用户ID匹配，以确保用户有权取消订单。如果不匹配，返回授权失败的错误消息
   - 提取卖家ID，从卖家的账户中扣除订单价格，同时将相同金额返还到买家的账户
   - 删除匹配的订单记录
3. 如果在上述步骤中未找到任何适用的订单，返回无效订单ID的错误消息
4. 查询订单详细信息集合，获取与该订单相关的已购书籍信息。遍历书籍信息，恢复库存，增加相应的库存数量
5. 创建一个新订单，状态设置为4，包括订单ID、用户ID、商店ID和订单价格，并将其插入到订单集合中
6. 如果在执行过程中发生任何异常，函数会捕获并返回状态码528

#### 5.3.3 auto_cancel_order

函数输入：

该函数不接受任何参数，

函数输出：

- 一个整数：状态码，200表示成功，528表示发生错误
- 一个字符串：描述操作结果的消息

函数流程：

1. 定义一个等待时间 `wait_time`，设置为20秒，用于判断未支付订单的自动取消时限
2. 获取当前的UTC时间 `now`，计算出一个时间点 `interval`，表示当前时间减去 `wait_time` 秒后的时间
3. 构建查询条件 `cursor`，用于查找未支付（状态为0）且创建时间早于 `interval` 的订单
4. 将待取消的订单信息存储在 `orders_to_cancel` 中
5. 如果找到待取消的订单，遍历这些订单并执行以下操作：
   - 提取每个订单的相关信息，包括订单ID、用户ID、商店ID和订单价格
   - 从订单集合中删除该订单，以实现订单取消
   - 查询已取消订单的书籍详细信息，并遍历这些书籍
   - 对每本书籍，恢复库存，增加相应数量
   - 如果库存恢复失败，返回库存不足的错误消息
6. 对于每个成功取消的订单，函数创建一个新的订单文档 `canceled_order`，将状态设置已取消，然后将其插入到订单集合中
7. 如果在执行过程中发生任何异常，函数将捕获异常并返回状态码528

#### 5.3.4 is_order_cancelled

函数输入：

- `self`：类实例的引用
- `order_id`：要检查的订单的唯一标识

函数输出：

- 一个整数：状态码，200表示成功，其他状态码表示不同的错误情况
- 一个字符串：描述操作结果的消息

函数流程：

1. 首先，在订单集合中查询，查找订单ID等于给定的 `order_id` 且已取消的订单
2. 如果找到符合条件的订单，说明该订单已被取消返回状态码200
3. 如果未找到符合条件的订单，返回错误消息

# 6.版本控制

我使用git作为版本管理的工具，在原来实验一的基础上将核心数据库迁移到了Postgres上

项目地址：[AquaOH/bookstore at homework2 (github.com)](https://github.com/AquaOH/bookstore/tree/homework2)

![image-20241226140836521](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241226140836521.png)



# 7.运行测试结果

实现基础功能+额外功能后，进行测试

#### 7.1 小数据库`book.db`

最终HTML 覆盖率报告储存在`results/book_db`中

![image-20241226152858111](C:\Users\Administrator\AppData\Roaming\Typora\typora-user-images\image-20241226152858111.png)

#### 7.2 大数据库`booklx.db`

最终HTML 覆盖率报告储存在`results/book_lx_db`中

详细终端输出将`results/console.log`

![image-20241226161435686](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20241226161435686.png)

## 8. 总结

本次实验通过将 MongoDB 迁移到 PostgreSQL，实现了更高效的数据管理和查询。通过合理设计数据库表结构和索引，优化了查询性能。同时，通过测试驱动开发，确保了代码的健壮性和高覆盖率。最终，项目实现了基础功能和附加功能，并通过了全面的测试