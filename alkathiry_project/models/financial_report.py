from odoo import _, fields, models


class AlkFinancialReport(models.AbstractModel):
    """Financial reporting engine over the immutable ledger (§23.5.3).

    Derives the three formal statements — Income Statement, Cash Flow and Balance
    Sheet — by aggregating ``alkathiry.transaction`` (revenue/expense/commission/
    topup/withdrawal lines) and the wallet balances. Because the ledger is
    insert-only and immutable, every figure is reproducible and audit-safe.
    """

    _name = "alkathiry.financial.report"
    _description = "Alkathiry Financial Report Engine"

    def _read_group_amount(self, domain, groupby):
        """Return {key: summed amount} for the given domain grouped by a field."""
        Txn = self.env["alkathiry.transaction"].sudo()
        rows = Txn._read_group(domain, groupby=[groupby], aggregates=["amount:sum"])
        result = {}
        for key, amount in rows:
            label = key.id if hasattr(key, "id") else key
            result[label or "other"] = amount or 0.0
        return result

    # ------------------------------------------------------------------
    # Income Statement
    # ------------------------------------------------------------------
    def income_statement(self, date_from=None, date_to=None):
        base = self._period_domain(date_from, date_to)
        Txn = self.env["alkathiry.transaction"].sudo()

        revenue_by_stream = self._read_group_amount(
            base + [("transaction_type", "in", ("revenue", "commission"))],
            "revenue_stream",
        )
        # Committee commission captured on redemption lines.
        committee_commission = sum(
            Txn.search(base + [("transaction_type", "=", "redemption"), ("direction", "=", "debit")])
            .mapped("commission_committee")
        )
        if committee_commission:
            revenue_by_stream["commission"] = (
                revenue_by_stream.get("commission", 0.0) + committee_commission
            )

        expenses = sum(
            Txn.search(base + [("transaction_type", "=", "expense")]).mapped("amount")
        )
        total_revenue = sum(revenue_by_stream.values())
        return {
            "revenue_by_stream": revenue_by_stream,
            "total_revenue": total_revenue,
            "total_expenses": expenses,
            "net_income": total_revenue - expenses,
        }

    # ------------------------------------------------------------------
    # Cash Flow
    # ------------------------------------------------------------------
    def cash_flow(self, date_from=None, date_to=None):
        base = self._period_domain(date_from, date_to)
        Txn = self.env["alkathiry.transaction"].sudo()
        inflow_types = ("revenue", "commission", "topup")
        outflow_types = ("withdrawal", "expense")
        inflows = sum(Txn.search(base + [("transaction_type", "in", inflow_types)]).mapped("amount"))
        outflows = sum(Txn.search(base + [("transaction_type", "in", outflow_types)]).mapped("amount"))
        return {
            "inflows": inflows,
            "outflows": outflows,
            "net_cash_flow": inflows - outflows,
        }

    # ------------------------------------------------------------------
    # Balance Sheet
    # ------------------------------------------------------------------
    def balance_sheet(self, date_to=None):
        Balance = self.env["alkathiry.balance"].sudo()
        # Assets: beneficiary wallet balances held by the platform.
        wallet_liabilities = sum(
            Balance.search([("balance_type_id.is_monetary", "=", True)]).mapped("current_amount")
        )
        income = self.income_statement(date_to=date_to)
        # Retained equity proxied by net income to date.
        equity = income["net_income"]
        assets = wallet_liabilities + equity
        return {
            "assets": assets,
            "liabilities": wallet_liabilities,
            "equity": equity,
        }

    # ------------------------------------------------------------------
    def _period_domain(self, date_from, date_to):
        domain = [("status", "=", "success")]
        if date_from:
            domain.append(("posted_at", ">=", fields.Datetime.to_datetime(date_from)))
        if date_to:
            domain.append(("posted_at", "<=", fields.Datetime.to_datetime(date_to)))
        return domain


class AlkFinancialReportWizard(models.TransientModel):
    """Admin-facing wizard that renders the three statements for a period."""

    _name = "alkathiry.financial.report.wizard"
    _description = "Alkathiry Financial Report"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To", default=fields.Date.context_today)

    total_revenue = fields.Float(readonly=True)
    total_expenses = fields.Float(readonly=True)
    net_income = fields.Float(readonly=True)
    cash_inflows = fields.Float(readonly=True)
    cash_outflows = fields.Float(readonly=True)
    net_cash_flow = fields.Float(readonly=True)
    total_assets = fields.Float(readonly=True)
    total_liabilities = fields.Float(readonly=True)
    equity = fields.Float(readonly=True)
    report_html = fields.Html(readonly=True)

    def action_generate(self):
        self.ensure_one()
        engine = self.env["alkathiry.financial.report"]
        inc = engine.income_statement(self.date_from, self.date_to)
        cf = engine.cash_flow(self.date_from, self.date_to)
        bs = engine.balance_sheet(self.date_to)
        self.write(
            {
                "total_revenue": inc["total_revenue"],
                "total_expenses": inc["total_expenses"],
                "net_income": inc["net_income"],
                "cash_inflows": cf["inflows"],
                "cash_outflows": cf["outflows"],
                "net_cash_flow": cf["net_cash_flow"],
                "total_assets": bs["assets"],
                "total_liabilities": bs["liabilities"],
                "equity": bs["equity"],
                "report_html": self._render_html(inc, cf, bs),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _render_html(self, inc, cf, bs):
        streams = "".join(
            f"<tr><td>{k.title()}</td><td style='text-align:right'>{v:,.2f}</td></tr>"
            for k, v in inc["revenue_by_stream"].items()
        )
        return _(
            """
            <h3>Income Statement</h3>
            <table class="table table-sm">
              %(streams)s
              <tr><th>Total Revenue</th><th style='text-align:right'>%(rev).2f</th></tr>
              <tr><td>Total Expenses</td><td style='text-align:right'>%(exp).2f</td></tr>
              <tr><th>Net Income</th><th style='text-align:right'>%(net).2f</th></tr>
            </table>
            <h3>Cash Flow</h3>
            <table class="table table-sm">
              <tr><td>Inflows</td><td style='text-align:right'>%(cin).2f</td></tr>
              <tr><td>Outflows</td><td style='text-align:right'>%(cout).2f</td></tr>
              <tr><th>Net Cash Flow</th><th style='text-align:right'>%(cnet).2f</th></tr>
            </table>
            <h3>Balance Sheet</h3>
            <table class="table table-sm">
              <tr><td>Assets</td><td style='text-align:right'>%(ast).2f</td></tr>
              <tr><td>Liabilities (wallet balances)</td><td style='text-align:right'>%(lia).2f</td></tr>
              <tr><th>Equity</th><th style='text-align:right'>%(eq).2f</th></tr>
            </table>
            """
        ) % {
            "streams": streams,
            "rev": inc["total_revenue"],
            "exp": inc["total_expenses"],
            "net": inc["net_income"],
            "cin": cf["inflows"],
            "cout": cf["outflows"],
            "cnet": cf["net_cash_flow"],
            "ast": bs["assets"],
            "lia": bs["liabilities"],
            "eq": bs["equity"],
        }
