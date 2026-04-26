from django.db import migrations


class Migration(migrations.Migration):
    """
    SQLite does not support ALTER COLUMN, so we recreate core_client
    with sales_rep having a proper DEFAULT '' at the database level.
    """

    dependencies = [
        ('core', '0004_client_sales_rep_default'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE "core_client_new" (
                "id" char(32) NOT NULL PRIMARY KEY,
                "company_id" char(32) NOT NULL REFERENCES "core_company" ("id") DEFERRABLE INITIALLY DEFERRED,
                "name" varchar(200) NOT NULL,
                "store_name" varchar(200) NOT NULL,
                "contact_name" varchar(100) NOT NULL,
                "email" varchar(254) NOT NULL,
                "daily_rate" decimal NOT NULL,
                "sales_rep" varchar(100) NOT NULL DEFAULT '',
                "payment_terms" varchar(100) NOT NULL,
                "invoice_method" varchar(10) NOT NULL,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL
            );
            INSERT INTO "core_client_new"
                SELECT "id", "company_id", "name", "store_name", "contact_name",
                       "email", "daily_rate", COALESCE("sales_rep", ''),
                       "payment_terms", "invoice_method", "created_at", "updated_at"
                FROM "core_client";
            DROP TABLE "core_client";
            ALTER TABLE "core_client_new" RENAME TO "core_client";
            CREATE INDEX "core_client_company_id_92a4db57"
                ON "core_client" ("company_id");
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
