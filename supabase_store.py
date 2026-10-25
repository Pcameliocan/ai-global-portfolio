"""Supabase PostgREST storage. Writes only through atomic PostgreSQL RPC."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class Store:
    def __init__(self, url, key):
        if not url or not key: raise RuntimeError('Missing Supabase configuration')
        self.url=url.rstrip('/')
        self.key=key

    def request(self, method, path, payload=None):
        body=json.dumps(payload,allow_nan=False).encode() if payload is not None else None
        req=Request(self.url+'/rest/v1/'+path,data=body,method=method,headers={
            'apikey':self.key,'Authorization':'Bearer '+self.key,
            'Content-Type':'application/json','Accept':'application/json'})
        try:
            with urlopen(req,timeout=30) as response:
                raw=response.read()
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            raise RuntimeError(f'Supabase HTTP {exc.code}: {exc.read().decode()[:500]}') from exc

    def state(self):
        rows=self.request('GET','paper_state?id=eq.1&select=*')
        if not rows: raise RuntimeError('paper_state row missing: run schema.sql first')
        return rows[0]

    def runs(self, limit=180):
        return self.request('GET',f'paper_runs?select=*&order=market_date.desc&limit={int(limit)}')

    def trades(self, limit=300):
        return self.request('GET',f'paper_trades?select=*&order=id.desc&limit={int(limit)}')

    def commit(self, expected_version, market_date, cash, holdings, pending, equity, spy_price, ranking, trades, rationale):
        return self.request('POST','rpc/commit_paper_day',{
            'p_expected_version':int(expected_version), 'p_market_date':market_date,
            'p_cash':cash,'p_holdings':holdings,'p_pending':pending,
            'p_equity':equity,'p_spy_price':spy_price,'p_ranking':ranking,
            'p_trades':trades,'p_rationale':rationale})
