import datetime
import json
import time
from contextlib import contextmanager
from typing import List, Mapping, Union

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Index,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT, insert
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from tradingview_zy import config, fun
from tradingview_zy.alert_strategy_storage import (
    normalize_strategy_config,
    normalize_strategy_memo,
)
from tradingview_zy.base import Market
from tradingview_zy.config import get_data_path
from tradingview_zy.database_catalog import list_market_kline_codes
from tradingview_zy.tv_storage import (
    TVStoragePolicy,
    enforce_quota,
    normalize_chart_payload,
    normalize_drawing_payload,
    utf8_size,
)

# https://docs.sqlalchemy.org/en/20/core/types.html

Base = declarative_base()
TV_BLOB_TEXT = Text().with_variant(MEDIUMTEXT(), "mysql")


class TableByCache(Base):
    # 各种乱七八杂的信息
    __tablename__ = "cl_cache"
    k = Column(String(100), unique=True, primary_key=True)  # 唯一值
    v = Column(Text, comment="存储内容")  # 存储内容
    expire = Column(
        Integer, default=0, comment="过期时间戳，0为永不过期"
    )  # 过期时间戳，0为永不过期
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByZxGroup(Base):
    # 自选组列表
    __tablename__ = "cl_zixuan_groups"
    __table_args__ = (
        UniqueConstraint("market", "zx_group", name="table_market_group_unique"),
    )
    market = Column(String(20), primary_key=True, comment="市场")
    zx_group = Column(String(20), primary_key=True, comment="自选组名称")
    add_dt = Column(DateTime, comment="添加时间")
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByZixuan(Base):
    # 自选表
    __tablename__ = "cl_zixuan_watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    zx_group = Column(String(20), comment="自选组")  # 自选组
    stock_code = Column(String(20), comment="标的代码")  # 标的代码
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    position = Column(Integer, comment="位置")  # 位置
    add_datetime = Column(DateTime, comment="添加时间")  # 添加时间
    stock_color = Column(String(20), comment="自选颜色")  # 自选颜色
    stock_memo = Column(String(100), comment="附加信息")  # 附加信息
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByAlertTask(Base):
    # 提醒任务
    __tablename__ = "cl_alert_task"
    __table_args__ = (
        UniqueConstraint("market", "task_name", name="table_market_task_name_unique"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    task_name = Column(String(100), comment="任务名称")  # 任务名称
    zx_group = Column(String(20), comment="自选组")  # 自选组
    frequency = Column(String(20), comment="检查周期")  # 检查周期
    interval_minutes = Column(Integer, comment="检查间隔分钟")  # 检查间隔分钟
    check_bi_type = Column(String(20), comment="检查笔的类型")  # 检查笔的类型
    check_bi_beichi = Column(String(200), comment="检查笔的背驰")  # 检查笔的背驰
    check_bi_mmd = Column(String(200), comment="检查笔的买卖点")  # 检查笔的买卖点
    check_xd_type = Column(String(20), comment="检查线段的类型")  # 检查线段的类型
    check_xd_beichi = Column(String(200), comment="检查线段的背驰")  # 检查线段的背驰
    check_xd_mmd = Column(String(200), comment="检查线段的买卖点")  # 检查线段的买卖点
    check_idx_ma_info = Column(String(200), comment="检查指数的均线")
    check_idx_macd_info = Column(String(200), comment="检查指数的MACD")
    strategy_config_text = Column(
        "strategy_config", Text, nullable=True, comment="版本化策略 JSON"
    )
    strategy_memo_text = Column(
        "strategy_memo", Text, nullable=True, comment="策略备注"
    )
    is_run = Column(Integer, comment="是否运行")  # 是否运行
    is_send_msg = Column(Integer, comment="是否发送消息")  # 是否发送消息
    dt = Column(DateTime, comment="任务添加、修改时间")  # 任务添加、修改时间
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}

    @property
    def strategy_config(self):
        return self.strategy_config_text or self.check_idx_ma_info or "{}"

    @property
    def strategy_memo(self):
        return self.strategy_memo_text or self.check_idx_macd_info or ""


class TableByAlertRecord(Base):
    # 提醒记录
    __tablename__ = "cl_alert_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    task_name = Column(String(100), comment="任务名称")  # 任务名称
    stock_code = Column(String(20), comment="标的")  # 标的
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    frequency = Column(String(10), comment="提醒周期")  # 提醒周期
    line_type = Column(String(5), comment="提醒线段的类型")  # 提醒线段的类型
    alert_msg = Column(Text, comment="提醒消息")  # 提醒消息
    bi_is_done = Column(
        String(10), comment="笔是否完成,如果是指标，则记录上穿或下穿"
    )  # 笔是否完成
    bi_is_td = Column(String(10), comment="笔是否停顿")  # 笔是否停顿
    line_dt = Column(DateTime, comment="提醒线段的开始时间")  # 提醒线段的开始时间
    alert_dt = Column(DateTime, comment="提醒时间")  # 提醒时间
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}

    @property
    def event_type(self):
        return self.line_type or ""

    @property
    def action(self):
        return self.bi_is_done or ""

    @property
    def score(self):
        return self.bi_is_td or ""

    @property
    def event_time(self):
        return self.line_dt


class TableByTVMarks(Base):
    # TV 图表的 mark 标记 (在时间轴上的标记)
    __tablename__ = "cl_tv_marks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    stock_code = Column(String(20), comment="标的代码")  # 标的代码
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    frequency = Column(String(10), default="", comment="展示周期")  # 展示周期
    mark_time = Column(Integer, comment="标签时间戳")  # 标签时间戳
    mark_label = Column(String(2), comment="标签")  # 标签
    mark_tooltip = Column(String(100), comment="提示")  # 提示
    mark_shape = Column(String(20), comment="形状")  # 形状
    mark_color = Column(String(20), comment="颜色")  # 颜色
    dt = Column(DateTime, comment="添加时间")
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByTVMarksPrice(Base):
    # TV 图表的 mark 标记 (在价格主图的标记)
    __tablename__ = "cl_tv_marks_price"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    stock_code = Column(String(20), comment="标的代码")  # 标的代码
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    frequency = Column(String(10), default="", comment="展示周期")  # 展示周期
    mark_time = Column(Integer, comment="标签时间戳")  # 标签时间戳
    mark_color = Column(String(20), comment="颜色")  # 颜色
    mark_text = Column(String(100), comment="提示")  # 提示
    mark_label = Column(String(2), comment="标签")  # 标签
    mark_label_font_color = Column(String(20), comment="标签字体颜色")  # 标签字体颜色
    mark_min_size = Column(Integer, comment="最小尺寸")  # 最小尺寸

    dt = Column(DateTime, comment="添加时间")
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByOrder(Base):
    # 订单
    __tablename__ = "cl_order"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    stock_code = Column(String(20), comment="标的代码")  # 标的代码
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    order_type = Column(String(20), comment="订单类型")  # 订单类型
    order_price = Column(Float, comment="订单价格")  # 订单价格
    order_amount = Column(Float, comment="订单数量")  # 订单数量
    order_memo = Column(String(200), comment="订单备注")  # 订单备注
    dt = Column(DateTime, comment="添加时间")  # 添加时间
    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByTVStorageOwner(Base):
    """Per TradingView namespace lock row used by transactional quota checks."""

    __tablename__ = "cl_tv_storage_owners"
    client_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), primary_key=True)
    timestamp = Column(Integer, nullable=False, default=0)
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


class TableByTVCharts(Base):
    # TV 图表的布局
    __tablename__ = "cl_tv_charts"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="id")
    client_id = Column(String(50), comment="客户端id")
    user_id = Column(String(50), comment="用户id")
    chart_type = Column(String(20), comment="布局类型")
    symbol = Column(String(50), comment="标的")
    resolution = Column(String(20), comment="周期")
    content = Column(TV_BLOB_TEXT, comment="布局内容")
    timestamp = Column(Integer, comment="时间戳")
    name = Column(String(50), comment="布局名称")
    __table_args__ = (
        UniqueConstraint(
            "chart_type",
            "client_id",
            "user_id",
            "name",
            name="table_tv_charts_owner_name_unique",
        ),
        Index(
            "table_tv_charts_owner_idx",
            "client_id",
            "user_id",
            "chart_type",
        ),
        {"mysql_collate": "utf8mb4_general_ci"},
    )


class TableByTVDrawings(Base):
    # TV 图表的手工绘图
    __tablename__ = "cl_tv_drawings"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="id")
    client_id = Column(String(100), comment="客户端id")
    user_id = Column(String(50), comment="用户id")
    layout_id = Column(String(100), comment="布局id")
    chart_id = Column(String(100), comment="图表id")
    symbol = Column(String(100), comment="标的")
    state = Column(TV_BLOB_TEXT, comment="绘图内容")
    timestamp = Column(Integer, comment="时间戳")
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "user_id",
            "layout_id",
            "chart_id",
            "symbol",
            name="table_tv_drawings_unique",
        ),
        Index("table_tv_drawings_owner_idx", "client_id", "user_id"),
        {"mysql_collate": "utf8mb4_general_ci"},
    )


class TableByAIAnalyse(Base):
    # AI 分析结果记录
    __tablename__ = "cl_ai_analyses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(20), comment="市场")  # 市场
    stock_code = Column(String(20), comment="标的")  # 标的
    stock_name = Column(String(100), comment="标的名称")  # 标的名称
    frequency = Column(String(10), comment="分析周期")
    dt = Column(DateTime, comment="分析时间")
    model = Column(String(100), comment="分析模型")
    prompt = Column(Text, comment="缠论当下说明")
    msg = Column(Text, comment="分析结果")

    # 添加配置设置编码
    __table_args__ = {"mysql_collate": "utf8mb4_general_ci"}


def build_mysql_url(
    *,
    username: str,
    password: str,
    host: str,
    port: int | str,
    database: str,
) -> URL:
    """Build a structured MySQL URL without interpolating credentials."""
    return URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=int(port),
        database=database,
        query={"charset": "utf8mb4"},
    )


def _watchlist_text(value, *, field: str, max_length: int, allow_empty: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError(f"{field} must be non-empty")
    if len(value) > max_length:
        raise ValueError(f"{field} exceeds {max_length} characters")
    return value


def normalize_watchlist_snapshot(stocks) -> list[dict[str, str]]:
    """Validate a complete watchlist snapshot before any existing rows are deleted.

    Duplicate codes keep their first position while the most recent signal updates
    the displayed name, memo and color.  This matches multi-frequency selection
    semantics without creating duplicate watchlist rows.
    """

    if not isinstance(stocks, (list, tuple)):
        raise TypeError("stocks must be a list or tuple")

    order: list[str] = []
    by_code: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(stocks):
        if not isinstance(raw, Mapping):
            raise TypeError(f"stocks[{index}] must be a mapping")
        code = _watchlist_text(
            raw.get("code"), field=f"stocks[{index}].code", max_length=20
        )
        raw_name = raw.get("name")
        if raw_name is None or (isinstance(raw_name, str) and not raw_name.strip()):
            raw_name = code
        name = _watchlist_text(
            raw_name, field=f"stocks[{index}].name", max_length=100
        )
        memo = _watchlist_text(
            raw.get("memo", ""),
            field=f"stocks[{index}].memo",
            max_length=100,
            allow_empty=True,
        )
        color = _watchlist_text(
            raw.get("color", ""),
            field=f"stocks[{index}].color",
            max_length=20,
            allow_empty=True,
        )
        if code not in by_code:
            order.append(code)
        by_code[code] = {
            "code": code,
            "name": name,
            "memo": memo,
            "color": color,
        }

    return [by_code[code] for code in order]


def migrate_alert_strategy_storage(engine) -> None:
    """Add dedicated TEXT columns to an existing alert table, idempotently."""
    inspector = inspect(engine)
    if not inspector.has_table(TableByAlertTask.__tablename__):
        return
    columns = {column["name"] for column in inspector.get_columns(TableByAlertTask.__tablename__)}
    statements = []
    if "strategy_config" not in columns:
        statements.append("ALTER TABLE cl_alert_task ADD COLUMN strategy_config TEXT")
    if "strategy_memo" not in columns:
        statements.append("ALTER TABLE cl_alert_task ADD COLUMN strategy_memo TEXT")
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(
            text(
                "UPDATE cl_alert_task SET strategy_config = check_idx_ma_info "
                "WHERE (strategy_config IS NULL OR strategy_config = '') "
                "AND check_idx_ma_info IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE cl_alert_task SET strategy_memo = check_idx_macd_info "
                "WHERE (strategy_memo IS NULL OR strategy_memo = '') "
                "AND check_idx_macd_info IS NOT NULL"
            )
        )


def migrate_tv_storage_schema(engine) -> None:
    """Upgrade legacy TradingView tables before quota-protected writes are allowed."""
    inspector = inspect(engine)
    if inspector.has_table(TableByTVCharts.__tablename__):
        with engine.begin() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, chart_type, client_id, user_id, name, timestamp "
                    "FROM cl_tv_charts ORDER BY timestamp DESC, id DESC"
                )
            ).mappings()
            seen = set()
            duplicate_ids = []
            for row in rows:
                key = (
                    row["chart_type"],
                    str(row["client_id"]),
                    str(row["user_id"]),
                    row["name"],
                )
                if key in seen:
                    duplicate_ids.append(int(row["id"]))
                else:
                    seen.add(key)
            for duplicate_id in duplicate_ids:
                connection.execute(
                    text("DELETE FROM cl_tv_charts WHERE id = :id"),
                    {"id": duplicate_id},
                )
            if engine.dialect.name == "mysql":
                connection.execute(
                    text("ALTER TABLE cl_tv_charts MODIFY COLUMN user_id VARCHAR(50)")
                )
                connection.execute(
                    text("ALTER TABLE cl_tv_charts MODIFY COLUMN content MEDIUMTEXT")
                )

        inspector = inspect(engine)
        index_names = {item["name"] for item in inspector.get_indexes("cl_tv_charts")}
        unique_names = {
            item.get("name")
            for item in inspector.get_unique_constraints("cl_tv_charts")
        }
        with engine.begin() as connection:
            if "table_tv_charts_owner_name_unique" not in index_names | unique_names:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX table_tv_charts_owner_name_unique "
                        "ON cl_tv_charts (chart_type, client_id, user_id, name)"
                    )
                )
            if "table_tv_charts_owner_idx" not in index_names:
                connection.execute(
                    text(
                        "CREATE INDEX table_tv_charts_owner_idx "
                        "ON cl_tv_charts (client_id, user_id, chart_type)"
                    )
                )

    inspector = inspect(engine)
    if inspector.has_table(TableByTVDrawings.__tablename__):
        if engine.dialect.name == "mysql":
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE cl_tv_drawings MODIFY COLUMN state MEDIUMTEXT")
                )
        inspector = inspect(engine)
        index_names = {item["name"] for item in inspector.get_indexes("cl_tv_drawings")}
        if "table_tv_drawings_owner_idx" not in index_names:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX table_tv_drawings_owner_idx "
                        "ON cl_tv_drawings (client_id, user_id)"
                    )
                )


@fun.singleton
class DB(object):
    global Base

    def __init__(self) -> None:
        if config.DB_TYPE == "sqlite":
            db_path = get_data_path() / "db"
            if db_path.is_dir() is False:
                db_path.mkdir(parents=True)
            self.engine = create_engine(
                f"sqlite:///{str(db_path / f'{config.DB_DATABASE}.sqlite')}",
                echo=False,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=10,
            )
        elif config.DB_TYPE == "mysql":
            self.engine = create_engine(
                build_mysql_url(
                    username=config.DB_USER,
                    password=config.DB_PWD,
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    database=config.DB_DATABASE,
                ),
                echo=False,
                poolclass=QueuePool,
                pool_recycle=3600,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                pool_timeout=10,
            )
        else:
            raise Exception("DB_TYPE 配置错误")

        self.Session = sessionmaker(bind=self.engine)

        Base.metadata.create_all(self.engine)
        migrate_alert_strategy_storage(self.engine)
        migrate_tv_storage_schema(self.engine)
        self.tv_storage_policy = TVStoragePolicy.from_config(config)

        self.__cache_tables = {}

    def klines_tables(self, market: str, stock_code: str):
        stock_code = (
            stock_code.replace(".", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace("@", "_")
            .lower()
        )
        if market == Market.HK.value:
            table_name = f"{market}_klines_{stock_code[-3:]}"
        elif market == Market.A.value:
            table_name = f"{market}_klines_{stock_code[:7]}"
        elif market == Market.US.value:
            table_name = f"{market}_klines_{stock_code[0]}"
        elif market == Market.FX.value:
            table_name = f"{market}_klines_{stock_code}"
        elif market == Market.CURRENCY.value:
            table_name = f"{market}_klines_{stock_code}"
        elif market == Market.CURRENCY_SPOT.value:
            table_name = f"{market}_klines_{stock_code}"
        elif market == Market.FUTURES.value:
            table_name = f"{market}_klines_{stock_code}"
        else:
            raise Exception(f"市场错误：{market}")

        if table_name in self.__cache_tables:
            return self.__cache_tables[table_name]

        class TableByKlines(Base):
            # 表名
            __tablename__ = table_name
            __table_args__ = (
                UniqueConstraint("code", "dt", "f", name="table_code_dt_f_unique"),
            )
            # 表结构
            code = Column(String(20), primary_key=True, comment="标的代码")
            dt = Column(DateTime, primary_key=True, comment="日期")
            f = Column(String(5), primary_key=True, comment="周期")
            o = Column(Float)
            c = Column(Float)
            h = Column(Float)
            l = Column(Float)
            v = Column(Float)
            # 添加配置设置编码
            __table_args__ = {
                "mysql_collate": "utf8mb4_general_ci",
            }

        if market == Market.FUTURES.value:
            # 期货市场，添加持仓列
            TableByKlines.p = Column(Float, comment="持仓量")

        self.__cache_tables[table_name] = TableByKlines
        Base.metadata.create_all(self.engine)
        return TableByKlines

    def klines_codes(self, market: str) -> List[str]:
        """Return the distinct instrument codes already stored for a market."""
        return list_market_kline_codes(self.engine, market)

    def klines_query(
        self,
        market: str,
        code: str,
        frequency: str,
        start_date: datetime.datetime = None,
        end_date: datetime.datetime = None,
        limit: int = 5000,
        order: str = "desc",
    ) -> List:
        """
        获取k线数据
        :param market:
        :param code:
        :param frequency:
        :param start_date:
        :param end_date:
        :param limit:
        :param order:
        :return:
        """
        with self.Session() as session:
            table = self.klines_tables(market, code)
            # 查询数据库
            filter = (table.code == code, table.f == frequency)
            if start_date is not None:
                filter += (table.dt >= start_date,)
            if end_date is not None:
                filter += (table.dt <= end_date,)
            query = session.query(table).filter(*filter)
            if order == "desc":
                query = query.order_by(table.dt.desc())
            else:
                query = query.order_by(table.dt.asc())
            if limit is not None:
                query = query.limit(limit)
            return query.all()

    def klines_last_datetime(self, market, code, frequency):
        """
        查询k线表中最后一条记录的日期
        :param market:
        :param code:
        :param frequency:
        :return:
        """
        with self.Session() as session:
            table = self.klines_tables(market, code)
            last_date = (
                session.query(table.dt)
                .filter(table.code == code)
                .filter(table.f == frequency)
                .order_by(table.dt.desc())
                .first()
            )
            if last_date is None:
                return None
            if market == "a":
                return last_date[0].strftime("%Y-%m-%d")
            else:
                return last_date[0].strftime("%Y-%m-%d %H:%M:%S")

    def klines_insert(
        self, market: str, code: str, frequency: str, klines: pd.DataFrame
    ):
        """
        插入k线
        :param market:
        :param code:
        :param frequency:
        :param klines:
        :return:
        """
        with self.Session() as session:
            table = self.klines_tables(market, code)

            # 如果是 sqlite ，则慢慢更新吧
            if config.DB_TYPE == "sqlite":
                for _, _k in klines.iterrows():
                    _in_k = {
                        "code": code,
                        "f": frequency,
                        "dt": _k["date"].replace(tzinfo=None),  # 去除时区信息
                        "o": _k["open"],
                        "c": _k["close"],
                        "h": _k["high"],
                        "l": _k["low"],
                        "v": _k["volume"],
                    }
                    if "position" in _k.keys():
                        _in_k["p"] = _k["position"]
                    db_k = (
                        session.query(table)
                        .filter(
                            table.code == code,
                            table.f == frequency,
                            table.dt == _in_k["dt"],
                        )
                        .first()
                    )
                    if db_k is None:
                        session.add(table(**_in_k))
                    else:
                        session.query(table).filter(
                            table.code == code,
                            table.f == frequency,
                            table.dt == _in_k["dt"],
                        ).update(_in_k)
                session.commit()
                return True

            # 将 klines 数据拆分为每 500 条一组，批量插入
            group = np.arange(len(klines)) // 500
            groups = [
                group.reset_index(drop=True) for _, group in klines.groupby(group)
            ]
            in_position = "position" in klines.columns
            for g_klines in groups:
                insert_klines = []
                for _, _k in g_klines.iterrows():
                    _insert_k = {
                        "code": code,
                        "dt": _k["date"].replace(tzinfo=None),  # 去除时区信息
                        "f": frequency,
                        "o": _k["open"],
                        "c": _k["close"],
                        "h": _k["high"],
                        "l": _k["low"],
                        "v": _k["volume"],
                    }
                    if in_position:
                        _insert_k["p"] = _k["position"]
                    insert_klines.append(_insert_k)
                insert_stmt = insert(table).values(insert_klines)
                update_keys = ["o", "c", "h", "l", "v"]
                if in_position:
                    update_keys.append("p")
                update_columns = {
                    x.name: x for x in insert_stmt.inserted if x.name in update_keys
                }
                upsert_stmt = insert_stmt.on_duplicate_key_update(**update_columns)
                session.execute(upsert_stmt)
                session.commit()

        return True

    def klines_delete(
        self,
        market: str,
        code: str,
        frequency: str = None,
        dt: datetime.datetime = None,
    ):
        """
        删除k线
        :param market:
        :param code:
        :param frequency:
        :param dt:
        :return:
        """
        with self.Session() as session:
            table = self.klines_tables(market, code)
            q = session.query(table).filter(table.code == code)
            if frequency is not None:
                q = q.filter(table.f == frequency)
            if dt is not None:
                q = q.filter(table.dt == dt)
            q.delete()
            session.commit()

        return True

    def zx_get_groups(self, market: str) -> List[TableByZxGroup]:
        """
        获取自选分组
        """
        with self.Session() as session:
            return (
                session.query(TableByZxGroup)
                .filter(TableByZxGroup.market == market)
                .order_by(TableByZxGroup.add_dt.asc())
                .all()
            )

    def zx_add_group(self, market: str, zx_group: str) -> bool:
        """
        添加自选分组
        """
        with self.Session() as session:
            session.add(
                TableByZxGroup(
                    market=market, zx_group=zx_group, add_dt=datetime.datetime.now()
                )
            )
            session.commit()

        return True

    def zx_del_group(self, market: str, zx_group: str) -> bool:
        """
        删除自选分组
        """
        with self.Session() as session:
            session.query(TableByZxGroup).filter(
                TableByZxGroup.market == market, TableByZxGroup.zx_group == zx_group
            ).delete()
            session.commit()

        return True

    def zx_get_group_stocks(self, market: str, zx_group: str) -> List[TableByZixuan]:
        """
        获取自选组下的股票列表
        """
        with self.Session() as session:
            stocks = (
                session.query(TableByZixuan)
                .filter(TableByZixuan.zx_group == zx_group)
                .filter(TableByZixuan.market == market)
                .order_by(TableByZixuan.position.asc())
                .all()
            )
        return stocks

    def zx_add_group_stock(
        self,
        market: str,
        zx_group: str,
        stock_code: str,
        stock_name: str,
        memo: str = "",
        color: str = "",
        location: str = "bottom",
    ):
        # Delete/reorder/insert are one business operation and must commit atomically.
        with self.Session.begin() as session:
            session.query(TableByZixuan).filter(
                TableByZixuan.market == market,
                TableByZixuan.zx_group == zx_group,
                TableByZixuan.stock_code == stock_code,
            ).delete()

            position = 0
            if location == "top":
                # Flush the delete, then compact only this market/group to 1..N.
                # This also avoids leaving a position gap when an existing item is
                # removed from the middle and reinserted at the top.
                session.flush()
                existing_rows = (
                    session.query(TableByZixuan)
                    .filter(TableByZixuan.market == market)
                    .filter(TableByZixuan.zx_group == zx_group)
                    .order_by(TableByZixuan.position, TableByZixuan.id)
                    .all()
                )
                for existing_position, existing_row in enumerate(existing_rows, start=1):
                    existing_row.position = existing_position
            else:
                max_position = (
                    session.query(func.max(TableByZixuan.position))
                    .filter(TableByZixuan.market == market)
                    .filter(TableByZixuan.zx_group == zx_group)
                    .scalar()
                )
                position = max_position + 1 if max_position is not None else 0
            session.add(
                TableByZixuan(
                    market=market,
                    zx_group=zx_group,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    stock_color=color,
                    position=position,
                    stock_memo=memo,
                    add_datetime=datetime.datetime.now(),
                )
            )

        return True

    def zx_replace_group_stocks(self, market: str, zx_group: str, stocks) -> bool:
        """Atomically replace one market/group with a validated full snapshot."""

        market = _watchlist_text(market, field="market", max_length=20)
        zx_group = _watchlist_text(zx_group, field="zx_group", max_length=20)
        snapshot = normalize_watchlist_snapshot(stocks)
        now = datetime.datetime.now()

        with self.Session.begin() as session:
            session.query(TableByZixuan).filter(
                TableByZixuan.market == market,
                TableByZixuan.zx_group == zx_group,
            ).delete(synchronize_session=False)
            for position, stock in enumerate(snapshot):
                session.add(
                    TableByZixuan(
                        market=market,
                        zx_group=zx_group,
                        stock_code=stock["code"],
                        stock_name=stock["name"],
                        stock_color=stock["color"],
                        position=position,
                        stock_memo=stock["memo"],
                        add_datetime=now,
                    )
                )
                # Surface constraints/triggers inside this transaction so any failure
                # rolls back both the delete and every preceding insert.
                session.flush()

        return True

    def zx_del_group_stock(self, market: str, zx_group: str, stock_code: str):
        with self.Session() as session:
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).filter(TableByZixuan.stock_code == stock_code).delete()
            session.commit()

        return True

    def zx_update_stock_color(
        self, market: str, zx_group: str, stock_code: str, color: str
    ):
        with self.Session() as session:
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).filter(TableByZixuan.stock_code == stock_code).update(
                {"stock_color": color}, synchronize_session=False
            )
            session.commit()

        return True

    def zx_update_stock_name(
        self, market: str, zx_group: str, stock_code: str, stock_name: str
    ):
        with self.Session() as session:
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).filter(TableByZixuan.stock_code == stock_code).update(
                {"stock_name": stock_name}, synchronize_session=False
            )
            session.commit()

        return True

    def zx_stock_sort_top(self, market: str, zx_group: str, stock_code: str):
        with self.Session() as session:
            # market、zx_group 结果下的 position + 1
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).update(
                {"position": TableByZixuan.position + 1}, synchronize_session=False
            )
            # 再将指定的股票 postition 更新为 0
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).filter(TableByZixuan.stock_code == stock_code).update(
                {"position": 0}, synchronize_session=False
            )
            session.commit()

        return True

    def zx_stock_sort_bottom(self, market: str, zx_group: str, stock_code: str):
        with self.Session() as session:
            # 获取 market zx_group 结果下最大的position
            max_position = (
                session.query(func.max(TableByZixuan.position))
                .filter(TableByZixuan.market == market)
                .filter(TableByZixuan.zx_group == zx_group)
                .scalar()
            )
            # 将 market zx_group stock_code 结果下的 position 更新为 max_position + 1
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).filter(TableByZixuan.stock_code == stock_code).update(
                {"position": max_position + 1}, synchronize_session=False
            )
            session.commit()

        return True

    def zx_clear_by_group(self, market: str, zx_group: str):
        with self.Session() as session:
            # 删除 market、zx_group 下所有的记录
            session.query(TableByZixuan).filter(TableByZixuan.market == market).filter(
                TableByZixuan.zx_group == zx_group
            ).delete(synchronize_session=False)
            session.commit()

        return True

    def zx_query_group_by_code(self, market: str, stock_code: str) -> List[str]:
        with self.Session() as session:
            # 查询 market 下 stock_code 的所有去重的 zx_group 记录
            return [
                _[0]
                for _ in (
                    session.query(TableByZixuan.zx_group)
                    .filter(TableByZixuan.market == market)
                    .filter(TableByZixuan.stock_code == stock_code)
                    .distinct()
                    .all()
                )
            ]

    def order_save(
        self,
        market: str,
        stock_code: str,
        stock_name: str,
        order_type: str,
        order_price: float,
        order_amount: float,
        order_memo: str,
        order_time: Union[str, datetime.datetime],
    ):
        with self.Session() as session:
            # 保存订单
            order = TableByOrder(
                market=market,
                stock_code=stock_code,
                stock_name=stock_name,
                order_type=order_type,
                order_price=order_price,
                order_amount=order_amount,
                order_memo=order_memo,
                dt=order_time,
            )
            session.add(order)
            session.commit()

        return True

    def order_query_by_code(self, market: str, stock_code: str) -> List[TableByOrder]:
        with self.Session() as session:
            # 查询 market 下 stock_code 的所有订单
            orders = (
                session.query(TableByOrder)
                .filter(TableByOrder.market == market)
                .filter(TableByOrder.stock_code == stock_code)
                .all()
            )

        # {
        #     "code": "SH.000001",
        #     "datetime": "2021-10-19 10:09:51",
        #     "type": "buy", (允许的值：buy 买入 sell 卖出  open_long 开多  close_long 平多 open_short 开空 close_short 平空)
        #     "price": 205.8,
        #     "amount": 300.0,
        #     "info": "涨涨涨"
        # }
        return [  # 兼容之前的
            {
                "code": _o.stock_code,
                "name": _o.stock_name,
                "datetime": _o.dt,
                "type": _o.order_type,
                "price": _o.order_price,
                "amount": _o.order_amount,
                "info": _o.order_memo,
            }
            for _o in orders
        ]

    def order_clear_by_code(self, market: str, stock_code: str):
        with self.Session() as session:
            # 清除 market 下 stock_code 的所有订单
            session.query(TableByOrder).filter(TableByOrder.market == market).filter(
                TableByOrder.stock_code == stock_code
            ).delete()
            session.commit()

        return True

    def task_save(
        self,
        market: str,
        task_name: str,
        zx_group: str,
        frequency: str,
        interval_minutes: int,
        check_bi_type: str,
        check_bi_beichi: str,
        check_bi_mmd: str,
        check_xd_type: str,
        check_xd_beichi: str,
        check_xd_mmd: str,
        check_idx_ma_info: str,
        check_idx_macd_info: str,
        is_run: int,
        is_send_msg: int,
    ):
        with self.Session() as session:
            # 保存任务
            session.add(
                TableByAlertTask(
                    market=market,
                    task_name=task_name,
                    zx_group=zx_group,
                    frequency=frequency,
                    interval_minutes=interval_minutes,
                    check_bi_type=check_bi_type,
                    check_bi_beichi=check_bi_beichi,
                    check_bi_mmd=check_bi_mmd,
                    check_xd_type=check_xd_type,
                    check_xd_beichi=check_xd_beichi,
                    check_xd_mmd=check_xd_mmd,
                    check_idx_ma_info=check_idx_ma_info,
                    check_idx_macd_info=check_idx_macd_info,
                    is_run=is_run,
                    is_send_msg=is_send_msg,
                    dt=datetime.datetime.now(),
                )
            )
            session.commit()

        return True

    def task_save_strategy(
        self,
        market: str,
        task_name: str,
        zx_group: str,
        frequency: str,
        interval_minutes: int,
        strategy_config: str,
        strategy_memo: str,
        is_run: int,
        is_send_msg: int,
    ):
        normalized_config = normalize_strategy_config(strategy_config)
        normalized_memo = normalize_strategy_memo(strategy_memo)
        with self.Session.begin() as session:
            task = TableByAlertTask(
                market=market,
                task_name=task_name,
                zx_group=zx_group,
                frequency=frequency,
                interval_minutes=interval_minutes,
                check_bi_type="",
                check_bi_beichi="",
                check_bi_mmd="",
                check_xd_type="",
                check_xd_beichi="",
                check_xd_mmd="",
                strategy_config_text=normalized_config,
                strategy_memo_text=normalized_memo,
                is_run=is_run,
                is_send_msg=is_send_msg,
                dt=datetime.datetime.now(),
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            if task.strategy_config_text != normalized_config or task.strategy_memo_text != normalized_memo:
                raise RuntimeError("strategy storage round-trip verification failed")
        return True

    def task_query(self, market: str = None, id: int = None) -> List[TableByAlertTask]:
        with self.Session() as session:
            # 查询任务
            query = session.query(TableByAlertTask)
            filter = ()
            if market is not None:
                filter += (TableByAlertTask.market == market,)
            if id is not None:
                filter += (TableByAlertTask.id == id,)
            if len(filter) > 0:
                return query.filter(*filter).all()
            return query.all()

    def task_delete(self, id: int):
        with self.Session() as session:
            # 删除任务
            session.query(TableByAlertTask).filter(TableByAlertTask.id == id).delete()
            session.commit()

        return True

    def task_update(
        self,
        id: int,
        market: str,
        task_name: str,
        zx_group: str,
        frequency: str,
        interval_minutes: int,
        check_bi_type: str,
        check_bi_beichi: str,
        check_bi_mmd: str,
        check_xd_type: str,
        check_xd_beichi: str,
        check_xd_mmd: str,
        check_idx_ma_info: str,
        check_idx_macd_info: str,
        is_run: int,
        is_send_msg: int,
    ):
        with self.Session() as session:
            session.query(TableByAlertTask).filter(
                TableByAlertTask.market == market,
                TableByAlertTask.id == id,
            ).update(
                {
                    TableByAlertTask.task_name: task_name,
                    TableByAlertTask.zx_group: zx_group,
                    TableByAlertTask.frequency: frequency,
                    TableByAlertTask.interval_minutes: interval_minutes,
                    TableByAlertTask.check_bi_type: check_bi_type,
                    TableByAlertTask.check_bi_beichi: check_bi_beichi,
                    TableByAlertTask.check_bi_mmd: check_bi_mmd,
                    TableByAlertTask.check_xd_type: check_xd_type,
                    TableByAlertTask.check_xd_beichi: check_xd_beichi,
                    TableByAlertTask.check_xd_mmd: check_xd_mmd,
                    TableByAlertTask.check_idx_ma_info: check_idx_ma_info,
                    TableByAlertTask.check_idx_macd_info: check_idx_macd_info,
                    TableByAlertTask.is_run: is_run,
                    TableByAlertTask.is_send_msg: is_send_msg,
                    TableByAlertTask.dt: datetime.datetime.now(),
                }
            )
            session.commit()
        return True

    def task_update_strategy(
        self,
        id: int,
        market: str,
        task_name: str,
        zx_group: str,
        frequency: str,
        interval_minutes: int,
        strategy_config: str,
        strategy_memo: str,
        is_run: int,
        is_send_msg: int,
    ):
        normalized_config = normalize_strategy_config(strategy_config)
        normalized_memo = normalize_strategy_memo(strategy_memo)
        with self.Session.begin() as session:
            task = (
                session.query(TableByAlertTask)
                .filter(
                    TableByAlertTask.market == market,
                    TableByAlertTask.id == id,
                )
                .one_or_none()
            )
            if task is None:
                raise LookupError(f"alert task not found: market={market!r}, id={id!r}")
            task.task_name = task_name
            task.zx_group = zx_group
            task.frequency = frequency
            task.interval_minutes = interval_minutes
            task.strategy_config_text = normalized_config
            task.strategy_memo_text = normalized_memo
            task.is_run = is_run
            task.is_send_msg = is_send_msg
            task.dt = datetime.datetime.now()
            session.flush()
            session.refresh(task)
            if task.strategy_config_text != normalized_config or task.strategy_memo_text != normalized_memo:
                raise RuntimeError("strategy storage round-trip verification failed")
        return True

    def alert_record_save(
        self,
        market: str,
        task_name: str,
        stock_code: str,
        stock_name: str,
        frequency: str,
        alert_msg: str,
        bi_is_done: str,
        bi_is_td: str,
        line_type: str,
        line_dt: datetime.datetime,
    ):
        """
        保存预警记录
        :param market:
        :param stock_code:
        :param stock_name:
        :param frequency:
        :param alert_msg:
        :param bi_is_down:
        :param bi_is_td:
        :param line_dt:
        :return:
        """
        with self.Session() as session:
            recored = TableByAlertRecord(
                market=market,
                task_name=task_name,
                stock_code=stock_code,
                stock_name=stock_name,
                frequency=frequency,
                alert_msg=alert_msg,
                bi_is_done=bi_is_done,
                bi_is_td=bi_is_td,
                line_type=line_type,
                line_dt=line_dt.replace(tzinfo=None),
                alert_dt=datetime.datetime.now(),
            )
            session.add(recored)
            session.commit()

        return True

    def alert_event_save(
        self,
        market: str,
        task_name: str,
        stock_code: str,
        stock_name: str,
        frequency: str,
        alert_msg: str,
        action: str,
        score: str,
        event_type: str,
        event_time: datetime.datetime,
    ):
        return self.alert_record_save(
            market=market,
            task_name=task_name,
            stock_code=stock_code,
            stock_name=stock_name,
            frequency=frequency,
            alert_msg=alert_msg,
            bi_is_done=action,
            bi_is_td=score,
            line_type=event_type,
            line_dt=event_time,
        )

    def alert_record_query_by_code(
        self,
        market: str,
        stock_code: str,
        frequency: str,
        line_type: str,
        line_dt: datetime.datetime,
    ) -> TableByAlertRecord:
        """
        查询预警记录
        :param market:
        :param stock_code:
        :param frequency:
        :param dt:
        :return:
        """
        with self.Session() as session:
            return (
                session.query(TableByAlertRecord)
                .filter(
                    TableByAlertRecord.market == market,
                    TableByAlertRecord.stock_code == stock_code,
                    TableByAlertRecord.frequency == frequency,
                    TableByAlertRecord.line_type == line_type,
                    TableByAlertRecord.line_dt == line_dt,
                )
                .order_by(TableByAlertRecord.alert_dt.desc())
                .first()
            )

    def alert_record_query(
        self, market: str, task_name: str = None
    ) -> List[TableByAlertRecord]:
        """
        查询预警记录
        :param market:
        :param stock_code:
        :param frequency:
        :param dt:
        :return:
        """
        with self.Session() as session:
            query = session.query(TableByAlertRecord)
            query = query.filter(TableByAlertRecord.market == market)
            if task_name:
                query = query.filter(TableByAlertRecord.task_name == task_name)
            return query.order_by(TableByAlertRecord.alert_dt.desc()).limit(100)

    def marks_add(
        self,
        market: str,
        stock_code: str,
        stock_name: str,
        frequency: str,
        mark_time: int,
        mark_label: str,
        mark_tooltip: str,
        mark_shape: str,
        mark_color: str,
    ):
        """
        添加代码在 tv 时间轴显示的信息
        :param market:
        :param stock_code:
        :param stock_name:
        :param frequency:   需要在什么周期显示，默认 ‘’，所有周期，可以是 'd', '30m', '5m' 这样之下指定周期下展示
        :param mark_time:   int 时间戳
        :param mark_label:  时间刻度标记的标签，英文字母，最大 两位
        :param mark_tooltip:    工具提示内容
        :param mark_shape:  "circle" | "earningUp" | "earningDown" | "earning" 形状
        :param mark_color: 颜色 rgb，比如 'red'  '#FF0000'
        :return:
        """
        with self.Session() as session:
            # 相同的 market,code/mark_time/mark_label 只能又一个，先删除一下
            session.query(TableByTVMarks).filter(
                TableByTVMarks.market == market,
                TableByTVMarks.stock_code == stock_code,
                TableByTVMarks.mark_time == mark_time,
                TableByTVMarks.mark_label == mark_label,
            ).delete()

            mark = TableByTVMarks(
                market=market,
                stock_code=stock_code,
                stock_name=stock_name,
                frequency=frequency,
                mark_time=mark_time,
                mark_label=mark_label,
                mark_tooltip=mark_tooltip,
                mark_shape=mark_shape,
                mark_color=mark_color,
                dt=datetime.datetime.now(),
            )
            session.add(mark)
            session.commit()

        return True

    def marks_query(
        self, market: str, stock_code: str, start_date: int = None
    ) -> List[TableByTVMarks]:
        """
        查询图表标记
        :param market:
        :param stock_code:
        :return:
        """
        with self.Session() as session:
            query = session.query(TableByTVMarks).filter(
                TableByTVMarks.market == market,
                TableByTVMarks.stock_code == stock_code,
            )
            if start_date is not None:
                query = query.filter(TableByTVMarks.mark_time >= start_date)

            return query.order_by(TableByTVMarks.mark_time.asc()).all()

    def marks_del(self, market: str, mark_label: str):
        with self.Session() as session:
            session.query(TableByTVMarks).filter(
                TableByTVMarks.market == market, TableByTVMarks.mark_label == mark_label
            ).delete()
            session.commit()

        return True

    def marks_add_by_price(
        self,
        market: str,
        stock_code: str,
        stock_name: str,
        frequency: str,
        mark_time: int,
        mark_label: str,
        mark_text: str,
        mark_label_color: str,
        mark_color: str,
    ):
        """
        添加代码在 tv 价格主图显示的信息
        """
        with self.Session() as session:
            # 相同的 market,code/mark_time/mark_label 只能有一个，先删除一下
            session.query(TableByTVMarks).filter(
                TableByTVMarks.market == market,
                TableByTVMarks.stock_code == stock_code,
                TableByTVMarks.mark_time == mark_time,
                TableByTVMarks.mark_label == mark_label,
            ).delete()

            mark = TableByTVMarksPrice(
                market=market,
                stock_code=stock_code,
                stock_name=stock_name,
                frequency=frequency,
                mark_time=mark_time,
                mark_color=mark_color,
                mark_text=mark_text,
                mark_label=mark_label,
                mark_label_font_color=mark_label_color,
                mark_min_size=1,
                dt=datetime.datetime.now(),
            )
            session.add(mark)
            session.commit()

        return True

    def marks_query_by_price(
        self, market: str, stock_code: str, start_date: int = None
    ) -> List[TableByTVMarksPrice]:
        """
        查询图表标记
        :param market:
        :param stock_code:
        :return:
        """
        with self.Session() as session:
            query = session.query(TableByTVMarksPrice).filter(
                TableByTVMarksPrice.market == market,
                TableByTVMarksPrice.stock_code == stock_code,
            )
            if start_date is not None:
                query = query.filter(TableByTVMarksPrice.mark_time >= start_date)
            return query.order_by(TableByTVMarksPrice.mark_time.asc()).all()

    def marks_del_by_price(self, market: str, mark_label: str):
        with self.Session() as session:
            session.query(TableByTVMarksPrice).filter(
                TableByTVMarks.market == market,
                TableByTVMarksPrice.mark_label == mark_label,
            ).delete()
            session.commit()

        return True

    def marks_del_all_by_code(self, market: str, code: str):
        """
        删除代码的所有标记
        """
        with self.Session() as session:
            session.query(TableByTVMarks).filter(
                TableByTVMarks.market == market,
                TableByTVMarks.stock_code == code,
            ).delete()
            session.query(TableByTVMarksPrice).filter(
                TableByTVMarksPrice.market == market,
                TableByTVMarksPrice.stock_code == code,
            ).delete()
            session.commit()
        return True

    @contextmanager
    def _tv_storage_write_session(self):
        session = self.Session()
        try:
            if self.engine.dialect.name == "sqlite":
                # SQLite ignores SELECT FOR UPDATE. Acquire the write lock before
                # any quota read so concurrent requests cannot both pass stale checks.
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _tv_storage_lock_owner(self, session, client_id: str, user_id: str) -> None:
        query = session.query(TableByTVStorageOwner).filter(
            TableByTVStorageOwner.client_id == client_id,
            TableByTVStorageOwner.user_id == user_id,
        )
        if self.engine.dialect.name != "sqlite":
            query = query.with_for_update()
        owner = query.one_or_none()
        if owner is None:
            owner = TableByTVStorageOwner(
                client_id=client_id, user_id=user_id, timestamp=int(time.time())
            )
            session.add(owner)
            session.flush()
            if self.engine.dialect.name != "sqlite":
                owner = (
                    session.query(TableByTVStorageOwner)
                    .filter(
                        TableByTVStorageOwner.client_id == client_id,
                        TableByTVStorageOwner.user_id == user_id,
                    )
                    .with_for_update()
                    .one()
                )
        owner.timestamp = int(time.time())

    @staticmethod
    def _tv_storage_usage(session, client_id: str, user_id: str):
        charts = (
            session.query(TableByTVCharts)
            .filter(
                TableByTVCharts.client_id == client_id,
                TableByTVCharts.user_id == user_id,
            )
            .all()
        )
        drawings = (
            session.query(TableByTVDrawings)
            .filter(
                TableByTVDrawings.client_id == client_id,
                TableByTVDrawings.user_id == user_id,
            )
            .all()
        )
        counts = {
            "chart": sum(1 for row in charts if row.chart_type == "chart"),
            "template": sum(1 for row in charts if row.chart_type == "template"),
            "drawing": len(drawings),
        }
        total = sum(utf8_size(row.content or "", field="content") for row in charts)
        total += sum(utf8_size(row.state or "", field="state") for row in drawings)
        return counts, total

    def tv_chart_list(self, chart_type, client_id, user_id):
        with self.Session() as session:
            return (
                session.query(TableByTVCharts)
                .filter(
                    TableByTVCharts.chart_type == chart_type,
                    TableByTVCharts.client_id == client_id,
                    TableByTVCharts.user_id == user_id,
                )
                .all()
            )

    def tv_chart_save(
        self, chart_type, client_id, user_id, name, content, symbol, resolution
    ):
        payload = normalize_chart_payload(
            self.tv_storage_policy,
            chart_type=chart_type,
            client_id=client_id,
            user_id=user_id,
            name=name,
            content=content,
            symbol=symbol,
            resolution=resolution,
        )
        with self._tv_storage_write_session() as session:
            self._tv_storage_lock_owner(session, payload["client_id"], payload["user_id"])
            chart = (
                session.query(TableByTVCharts)
                .filter(
                    TableByTVCharts.chart_type == payload["chart_type"],
                    TableByTVCharts.client_id == payload["client_id"],
                    TableByTVCharts.user_id == payload["user_id"],
                    TableByTVCharts.name == payload["name"],
                )
                .one_or_none()
            )
            counts, current_total = self._tv_storage_usage(
                session, payload["client_id"], payload["user_id"]
            )
            old_bytes = utf8_size(chart.content or "", field="content") if chart else 0
            new_bytes = utf8_size(payload["content"], field="content")
            enforce_quota(
                self.tv_storage_policy,
                kind=chart_type,
                current_count=counts[chart_type],
                projected_count=counts[chart_type] + (0 if chart else 1),
                current_total_bytes=current_total,
                projected_total_bytes=current_total - old_bytes + new_bytes,
            )
            if chart is None:
                chart = TableByTVCharts(**payload)
                session.add(chart)
            else:
                chart.content = payload["content"]
                chart.symbol = payload["symbol"]
                chart.resolution = payload["resolution"]
            chart.timestamp = int(time.time())
            session.flush()
            saved_id = chart.id
        return saved_id

    def tv_chart_update(
        self, chart_type, id, client_id, user_id, name, content, symbol, resolution
    ):
        payload = normalize_chart_payload(
            self.tv_storage_policy,
            chart_type=chart_type,
            client_id=client_id,
            user_id=user_id,
            name=name,
            content=content,
            symbol=symbol,
            resolution=resolution,
        )
        with self._tv_storage_write_session() as session:
            self._tv_storage_lock_owner(session, payload["client_id"], payload["user_id"])
            chart = (
                session.query(TableByTVCharts)
                .filter(
                    TableByTVCharts.id == id,
                    TableByTVCharts.chart_type == chart_type,
                    TableByTVCharts.client_id == payload["client_id"],
                    TableByTVCharts.user_id == payload["user_id"],
                )
                .one_or_none()
            )
            if chart is None:
                return False
            duplicate = (
                session.query(TableByTVCharts.id)
                .filter(
                    TableByTVCharts.id != id,
                    TableByTVCharts.chart_type == chart_type,
                    TableByTVCharts.client_id == payload["client_id"],
                    TableByTVCharts.user_id == payload["user_id"],
                    TableByTVCharts.name == payload["name"],
                )
                .first()
            )
            if duplicate is not None:
                raise ValueError("a chart or template with this name already exists")
            counts, current_total = self._tv_storage_usage(
                session, payload["client_id"], payload["user_id"]
            )
            old_bytes = utf8_size(chart.content or "", field="content")
            new_bytes = utf8_size(payload["content"], field="content")
            enforce_quota(
                self.tv_storage_policy,
                kind=chart_type,
                current_count=counts[chart_type],
                projected_count=counts[chart_type],
                current_total_bytes=current_total,
                projected_total_bytes=current_total - old_bytes + new_bytes,
            )
            chart.name = payload["name"]
            chart.content = payload["content"]
            chart.symbol = payload["symbol"]
            chart.resolution = payload["resolution"]
            chart.timestamp = int(time.time())
            session.flush()
        return True

    def tv_chart_get(self, chart_type, id, client_id, user_id):
        # 获取图表布局
        with self.Session() as session:
            return (
                session.query(TableByTVCharts)
                .filter(
                    TableByTVCharts.id == id,
                    TableByTVCharts.chart_type == chart_type,
                    TableByTVCharts.client_id == client_id,
                    TableByTVCharts.user_id == user_id,
                )
                .first()
            )

    def tv_chart_get_by_name(self, chart_type, name, client_id, user_id):
        # 获取图表布局
        with self.Session() as session:
            return (
                session.query(TableByTVCharts)
                .filter(
                    TableByTVCharts.name == name,
                    TableByTVCharts.chart_type == chart_type,
                    TableByTVCharts.client_id == client_id,
                    TableByTVCharts.user_id == user_id,
                )
                .first()
            )

    def tv_chart_del(self, chart_type, id, client_id, user_id):
        # 删除图表布局
        with self.Session() as session:
            session.query(TableByTVCharts).filter(
                TableByTVCharts.id == id,
                TableByTVCharts.chart_type == chart_type,
                TableByTVCharts.client_id == client_id,
                TableByTVCharts.user_id == user_id,
            ).delete()
            session.commit()
        return True

    def tv_chart_del_by_name(self, chart_type, name, client_id, user_id):
        # 根据名称删除图表布局
        with self.Session() as session:
            session.query(TableByTVCharts).filter(
                TableByTVCharts.name == name,
                TableByTVCharts.chart_type == chart_type,
                TableByTVCharts.client_id == client_id,
                TableByTVCharts.user_id == user_id,
            ).delete()
            session.commit()
        return True

    def tv_drawing_get(self, client_id, user_id, layout_id, chart_id, symbol):
        # 获取图表手工绘图
        with self.Session() as session:
            filters = [
                TableByTVDrawings.client_id == client_id,
                TableByTVDrawings.user_id == user_id,
                TableByTVDrawings.layout_id == layout_id,
                TableByTVDrawings.chart_id == chart_id,
            ]
            drawing = (
                session.query(TableByTVDrawings)
                .filter(*filters, TableByTVDrawings.symbol == symbol)
                .first()
            )
            if drawing is None and symbol != "":
                drawing = (
                    session.query(TableByTVDrawings)
                    .filter(*filters, TableByTVDrawings.symbol == "")
                    .first()
                )
            return drawing.state if drawing else None

    def tv_drawing_save_or_update(
        self, client_id, user_id, layout_id, chart_id, symbol, state
    ):
        payload = normalize_drawing_payload(
            self.tv_storage_policy,
            client_id=client_id,
            user_id=user_id,
            layout_id=layout_id,
            chart_id=chart_id,
            symbol=symbol,
            state=state,
        )
        with self._tv_storage_write_session() as session:
            self._tv_storage_lock_owner(session, payload["client_id"], payload["user_id"])
            drawing = (
                session.query(TableByTVDrawings)
                .filter(
                    TableByTVDrawings.client_id == payload["client_id"],
                    TableByTVDrawings.user_id == payload["user_id"],
                    TableByTVDrawings.layout_id == payload["layout_id"],
                    TableByTVDrawings.chart_id == payload["chart_id"],
                    TableByTVDrawings.symbol == payload["symbol"],
                )
                .one_or_none()
            )
            counts, current_total = self._tv_storage_usage(
                session, payload["client_id"], payload["user_id"]
            )
            old_bytes = utf8_size(drawing.state or "", field="state") if drawing else 0
            new_bytes = utf8_size(payload["state"], field="state")
            enforce_quota(
                self.tv_storage_policy,
                kind="drawing",
                current_count=counts["drawing"],
                projected_count=counts["drawing"] + (0 if drawing else 1),
                current_total_bytes=current_total,
                projected_total_bytes=current_total - old_bytes + new_bytes,
            )
            if drawing is None:
                drawing = TableByTVDrawings(**payload)
                session.add(drawing)
            else:
                drawing.state = payload["state"]
            drawing.timestamp = int(time.time())
            session.flush()
        return True

    def cache_get(self, key: str):
        with self.Session() as session:
            # 获取当前时间戳
            now = int(time.time())
            # 获取缓存数据
            cache = session.query(TableByCache).filter(TableByCache.k == key).first()
            # 缓存数据存在，且缓存数据未过期
            if cache and (cache.expire == 0 or cache.expire > now):
                return json.loads(cache.v)
            # 缓存数据不存在，或缓存数据已过期
            # 删除过期缓存数据，expire_time != 0 and expire_time < now
            session.query(TableByCache).filter(
                TableByCache.expire != 0, TableByCache.expire < now
            ).delete()
            session.commit()

        return None

    def cache_set(self, key: str, val: dict, expire: int = 0):
        with self.Session() as session:
            session.query(TableByCache).filter(TableByCache.k == key).delete()
            cache = TableByCache(k=key, v=json.dumps(val), expire=expire)
            session.add(cache)
            session.commit()

        return True

    def cache_del(self, key: str):
        with self.Session() as session:
            session.query(TableByCache).filter(TableByCache.k == key).delete()
            session.commit()

        return True


db: DB = DB()
