from supabase import create_client, Client
from datetime import datetime
import os

supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

class ContractManager:
    @staticmethod
    def create_contract(data):
        # Add default status values
        data.update({
            'agent_status': 'pending',
            'client_status': 'pending',
            'status': 'pending'
        })
        return supabase.table('contracts').insert(data).execute()

    @staticmethod
    def get_contract(contract_id):
        return supabase.table('contracts').select('*').eq('id', contract_id).execute()

    @staticmethod
    def update_contract(contract_id, data):
        return supabase.table('contracts').update(data).eq('id', contract_id).execute()

    @staticmethod
    def get_all_contracts():
        return supabase.table('contracts').select('*').execute()