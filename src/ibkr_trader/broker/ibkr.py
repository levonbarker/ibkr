"""Real IBKR broker, backed by ``ib_async``.

This is the only module that imports ``ib_async``. Everything else depends on
the :class:`~ibkr_trader.broker.base.Broker` protocol.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from ib_async import IB, Contract, LimitOrder, MarketOrder, MutualFund, Order, Stock

from ibkr_trader.broker.base import OpenOrder, Position
from ibkr_trader.core.config import GatewayConfig
from ibkr_trader.core.intent import Instrument, Intent, Result
from ibkr_trader.util.logging import get_logger

log = get_logger("broker.ibkr")

_YIELD_RE = re.compile(r"<Yield[^>]*>([-0-9.]+)</Yield>", re.IGNORECASE)


def _to_instrument(contract: Contract) -> Instrument:
    return Instrument(
        symbol=contract.symbol,
        sec_type=contract.secType or "STK",
        exchange=contract.exchange or "SMART",
        currency=contract.currency or "USD",
        primary_exchange=contract.primaryExchange or "",
        con_id=contract.conId or 0,
    )


class IbkrBroker:
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.ib = IB()

    def connect(self) -> None:
        log.info(
            "connecting to %s:%s clientId=%s",
            self.config.host,
            self.config.port,
            self.config.client_id,
        )
        self.ib.connect(
            self.config.host,
            self.config.port,
            clientId=self.config.client_id,
            timeout=self.config.timeout,
            readonly=self.config.readonly,
        )

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    # -- accounts -----------------------------------------------------------
    def accounts(self) -> list[str]:
        return list(self.ib.managedAccounts())

    def account_values(self, account: str) -> dict[str, Decimal]:
        values: dict[str, Decimal] = {}
        for item in self.ib.accountValues(account):
            if not item.currency or item.currency == "BASE":
                values[item.tag] = _dec(item.value)
        return values

    def account_currency_balances(self, account: str) -> dict[str, Decimal]:
        balances: dict[str, Decimal] = {}
        for item in self.ib.accountValues(account):
            if item.tag == "CashBalance" and item.currency:
                balances[item.currency] = _dec(item.value)
        return balances

    def positions(self, account: str) -> list[Position]:
        return [
            Position(
                account=p.account,
                instrument=_to_instrument(p.contract),
                quantity=_dec(p.position),
                average_cost=_dec(p.avgCost),
            )
            for p in self.ib.positions(account)
        ]

    def open_orders(self, account: str) -> list[OpenOrder]:
        orders: list[OpenOrder] = []
        for trade in self.ib.openTrades():
            if trade.order.account and trade.order.account != account:
                continue
            orders.append(
                OpenOrder(
                    account=trade.order.account or account,
                    order_ref=trade.order.orderRef or "",
                    instrument=_to_instrument(trade.contract),
                    side=trade.order.action,
                    status=trade.orderStatus.status,
                )
            )
        return orders

    # -- contracts ----------------------------------------------------------
    def qualify(self, instrument: Instrument) -> Instrument:
        contract = self._contract(instrument)
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"could not qualify {instrument.label}")
        return _to_instrument(qualified[0])

    def _contract(self, instrument: Instrument) -> Contract:
        if instrument.sec_type == "MUTUALFUND":
            return MutualFund(
                symbol=instrument.symbol,
                exchange=instrument.exchange or "",
                currency=instrument.currency,
            )
        if instrument.sec_type in ("STK", "ETF"):
            return Stock(
                symbol=instrument.symbol,
                exchange=instrument.exchange or "SMART",
                currency=instrument.currency,
            )
        return Contract(
            symbol=instrument.symbol,
            secType=instrument.sec_type,
            exchange=instrument.exchange,
            currency=instrument.currency,
        )

    # -- orders -------------------------------------------------------------
    def place_order(self, intent: Intent) -> Result:
        contract = self._contract(intent.instrument)
        if intent.cash_quantity is not None:
            order = Order(
                action=intent.side,
                orderType="MKT",
                totalQuantity=0.0,
                cashQty=float(intent.cash_quantity),
            )
        elif intent.order_type == "LMT" and intent.limit_price is not None:
            order = LimitOrder(intent.side, float(intent.quantity or 0), float(intent.limit_price))
        else:
            order = MarketOrder(intent.side, float(intent.quantity or 0))

        order.account = intent.account
        order.orderRef = intent.order_ref

        trade = self.ib.placeOrder(contract, order)
        self.ib.sleep(1)
        status = trade.orderStatus.status
        result = Result(
            intent=intent,
            status="SUBMITTED",
            message=f"order {status}",
            order_id=trade.order.orderId,
            broker_status=status,
        )
        log.info("placed %s %s -> %s", intent.side, intent.instrument.symbol, status)
        return result

    # -- market data --------------------------------------------------------
    def last_price(self, instrument: Instrument) -> Decimal | None:
        contract = self._contract(instrument)
        ticker = self.ib.reqMktData(contract, "", snapshot=True)
        self.ib.sleep(2)
        price = ticker.marketPrice() or ticker.close
        self.ib.cancelMktData(contract)
        return _dec(price) if price else None

    def dividend_yield(self, instrument: Instrument) -> Decimal | None:
        contract = self._contract(instrument)
        ticker = self.ib.reqMktData(contract, genericTickList="456", snapshot=True)
        self.ib.sleep(2)
        dividends = getattr(ticker, "dividends", None)
        price = ticker.marketPrice() or ticker.close
        self.ib.cancelMktData(contract)
        if not dividends or not price:
            return None
        annual = dividends.next12Months or dividends.past12Months
        if not annual:
            return None
        return (Decimal(str(annual)) / Decimal(str(price)) * 100).quantize(Decimal("0.0001"))

    def fund_yield(self, instrument: Instrument) -> Decimal | None:
        contract = self._contract(instrument)
        try:
            xml = self.ib.reqFundamentalData(contract, "ReportsFinSummary")
        except Exception as exc:  # noqa: BLE001
            log.warning("fundamental data failed for %s: %s", instrument.symbol, exc)
            return None
        match = _YIELD_RE.search(xml or "")
        return _dec(match.group(1)) if match else None


def _dec(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
