from lnbits.db import Database

db2 = Database("ext_lnurlpos")


async def m001_initial(db):
    """
    Initial lnpos table.
    """
    await db.execute(
        f"""
        CREATE TABLE lnpos.lnpos (
            id TEXT NOT NULL PRIMARY KEY,
            key TEXT NOT NULL,
            title TEXT NOT NULL,
            wallet TEXT NOT NULL,
            currency TEXT NOT NULL,
            profit FLOAT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )
    await db.execute(
        f"""
        CREATE TABLE lnpos.lnpos_payment (
            id TEXT NOT NULL PRIMARY KEY,
            lnpos_id TEXT NOT NULL,
            payment_hash TEXT,
            pin INTEGER,
            sats {db.big_int},
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )

async def m002_add_cents_to_lnpos_payment(db):
    """
    Add cents column to lnpos_payment table.
    """
    await db.execute("ALTER TABLE lnpos.lnpos_payment ADD COLUMN cents INTEGER;")
