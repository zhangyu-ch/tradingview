from __future__ import annotations

import datetime as dt
import math

import pytest

from tradingview_zy.domain import (
    Fill,
    InvalidRequestError,
    OrderRequest,
    OrderSide,
    OrderState,
    OrderStatus,
)


def test_order_request_rejects_invalid_primitive_values():
    with pytest.raises(InvalidRequestError, match="有限正数"):
        OrderRequest(
            market="a",
            code="SH.600000",
            side=OrderSide.BUY,
            amount=math.nan,
            client_order_id="client-1",
        )
    with pytest.raises(InvalidRequestError, match="限价"):
        OrderRequest(
            market="a",
            code="SH.600000",
            side=OrderSide.BUY,
            amount=100,
            client_order_id="client-1",
            limit_price=0,
        )


def test_fill_requires_timezone_and_order_state_reconciles_fill_quantity():
    with pytest.raises(InvalidRequestError, match="带时区"):
        Fill(
            order_id="provider-1",
            fill_id="fill-1",
            code="SH.600000",
            side=OrderSide.BUY,
            amount=100,
            price=10,
            fee=1,
            filled_at=dt.datetime(2026, 1, 2, 9, 30),
        )

    fill = Fill(
        order_id="provider-1",
        fill_id="fill-1",
        code="SH.600000",
        side=OrderSide.BUY,
        amount=40,
        price=10,
        fee=1,
        filled_at=dt.datetime(2026, 1, 2, 9, 30, tzinfo=dt.timezone.utc),
    )
    state = OrderState(
        client_order_id="client-1",
        provider_order_id="provider-1",
        status=OrderStatus.PARTIALLY_FILLED,
        requested_amount=100,
        filled_amount=40,
        average_fill_price=10,
        fills=(fill,),
    )
    assert state.status.terminal is False

    with pytest.raises(InvalidRequestError, match="成交明细"):
        OrderState(
            client_order_id="client-1",
            provider_order_id="provider-1",
            status=OrderStatus.PARTIALLY_FILLED,
            requested_amount=100,
            filled_amount=50,
            fills=(fill,),
        )
