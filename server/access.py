"""Commercial integration seam, deliberately dormant.

All local features are available. A future hosted data provider must authenticate
and enforce access server-side; client flags are not a billing or security boundary.
Blizzard policies must be reviewed before offering any paid service or content.
"""
from typing import Protocol

FEATURES=('market-data','arbitrage','crafting','housing','lumber','inventory','analytics')

class DataAccessProvider(Protocol):
    def authorize(self,principal:str,feature:str)->bool: ...

class SelfHostedAccess:
    def authorize(self,principal,feature):return feature in FEATURES
    def describe(self):return dict(provider='self-hosted',billing_enabled=False,features={key:True for key in FEATURES})
