from django.db.models import Lookup
from django.apps import apps


class TCPPortExactOverride(Lookup):
    lookup_name = 'exact'

    def as_sql(self, compiler, connection, **extra_context):
        lhs, rhs = self.get_source_expressions(), self.get_prep_lookup()

        # Convert rhs (input port) to an integer
        try:
            rhs_value = int(rhs)
        except ValueError:
            return "", []  # Invalid input, return empty result

        # Compile lhs (tcp_portrange field) into a SQL expression
        lhs_sql, params = compiler.compile(lhs[0])

        # If tcp_portrange is empty or invalid, return no results
        if lhs_sql == '' or lhs_sql is None:
            return "FALSE", []

        # SQL query: Include conditions for exact match, list match, and range match
        sql = f"""
            (
                -- Directly include 'ALL' if it matches criteria
                public.cmdb_service.name = 'ALL'
                AND public.cmdb_service.protocol = 'IP'
                AND public.cmdb_service.protocol_number = 0
                AND (public.cmdb_service.tcp_portrange IS NULL OR public.cmdb_service.tcp_portrange = '')

                OR EXISTS (
                    -- Check for individual ports only (skip ranges like "20-21")
                    SELECT 1
                    FROM unnest(string_to_array(public.cmdb_service.tcp_portrange, ' ')) AS val
                    WHERE
                        -- Extract the part before ':' (destination port)
                        LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1)) > 0
                        AND LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2)) = 0
                        AND CAST(SPLIT_PART(val, ':', 1) AS INTEGER) = %s
                )
                OR EXISTS (
                    -- Check for port ranges
                    SELECT 1
                    FROM unnest(string_to_array(public.cmdb_service.tcp_portrange, ' ')) AS val
                    WHERE
                        -- Extract the part before ':' (destination port range)
                        LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1)) > 0
                        AND LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2)) > 0
                        AND CAST(%s AS INTEGER) BETWEEN
                            CAST(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1) AS INTEGER)
                            AND CAST(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2) AS INTEGER)
                )

            )
        """

        params = [rhs_value, rhs_value]
        return sql, params



class UDPPortExactOverride(Lookup):
    lookup_name = 'exact'

    def as_sql(self, compiler, connection, **extra_context):
        lhs, rhs = self.get_source_expressions(), self.get_prep_lookup()

        # Convert rhs (input port) to an integer
        try:
            rhs_value = int(rhs)
        except ValueError:
            return "", []  # Invalid input, return empty result

        # Compile lhs (udp_portrange field) into a SQL expression
        lhs_sql, params = compiler.compile(lhs[0])

        # If udp_portrange is empty or invalid, return no results
        if lhs_sql == '' or lhs_sql is None:
            return "FALSE", []

        # SQL query: Include conditions for exact match, list match, and range match
        sql = f"""
            (
                -- Directly include 'ALL' if it matches criteria
                public.cmdb_service.name = 'ALL'
                AND public.cmdb_service.protocol = 'IP'
                AND public.cmdb_service.protocol_number = 0
                AND (public.cmdb_service.udp_portrange IS NULL OR public.cmdb_service.udp_portrange = '')

                OR EXISTS (
                    -- Check for individual ports only (skip ranges like "20-21")
                    SELECT 1
                    FROM unnest(string_to_array(public.cmdb_service.udp_portrange, ' ')) AS val
                    WHERE
                        -- Extract the part before ':' (destination port)
                        LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1)) > 0
                        AND LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2)) = 0
                        AND CAST(SPLIT_PART(val, ':', 1) AS INTEGER) = %s
                )
                OR EXISTS (
                    -- Check for port ranges
                    SELECT 1
                    FROM unnest(string_to_array(public.cmdb_service.udp_portrange, ' ')) AS val
                    WHERE
                        -- Extract the part before ':' (destination port range)
                        LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1)) > 0
                        AND LENGTH(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2)) > 0
                        AND CAST(%s AS INTEGER) BETWEEN
                            CAST(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 1) AS INTEGER)
                            AND CAST(SPLIT_PART(SPLIT_PART(val, ':', 1), '-', 2) AS INTEGER)
                )

            )
        """

        params = [rhs_value, rhs_value]
        return sql, params
    
def register_lookups():
    Service = apps.get_model('netbox_fortigate', 'Services')  # Dynamically get the model
    Service._meta.get_field('tcp_portrange').register_lookup(TCPPortExactOverride)
    Service._meta.get_field('udp_portrange').register_lookup(UDPPortExactOverride)


