from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from models import ContractManager
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import os
from datetime import datetime
from weasyprint import HTML
from io import BytesIO
import base64

app = Flask(__name__)
app.config.from_object(Config)
sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))

@app.route('/create_contract', methods=['GET', 'POST'])
def create_contract():
    form = ContractForm()
    if form.validate_on_submit():
        contract_data = {
            'client_name': form.client_name.data,
            'client_email': form.client_email.data,
            'agent_email': form.agent_email.data,
            'project_scope': form.project_scope.data,
            'total_amount': float(form.total_amount.data),
            'start_date': form.start_date.data.isoformat(),
            'end_date': form.end_date.data.isoformat(),
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = ContractManager.create_contract(contract_data)
        contract_id = result.data[0]['id']
        
        # Send emails to both parties
        send_contract_emails(contract_data, contract_id)
        
        flash('Contract created successfully!', 'success')
        return redirect(url_for('view_contract', contract_id=contract_id))
    return render_template('create_contract.html', form=form)

def send_contract_emails(contract_data, contract_id):
    # Create unique URLs for each recipient with their email embedded
    client_url = url_for('sign_contract', 
                        contract_id=contract_id, 
                        email=contract_data['client_email'],
                        _external=True)
    
    agent_url = url_for('sign_contract', 
                       contract_id=contract_id, 
                       email=contract_data['agent_email'],
                       _external=True)
    
    # Email to client
    client_message = Mail(
        from_email=os.getenv('SENDGRID_FROM_EMAIL'),
        to_emails=contract_data['client_email'],
        subject='New Contract for Signature',
        html_content=render_template('email/contract_notification.html',
                                   contract=contract_data,
                                   signing_url=client_url)
    )
    
    # Email to agent
    agent_message = Mail(
        from_email=os.getenv('SENDGRID_FROM_EMAIL'),
        to_emails=contract_data['agent_email'],
        subject='New Contract Created',
        html_content=render_template('email/contract_notification.html',
                                   contract=contract_data,
                                   signing_url=agent_url)
    )
    
    try:
        sg.send(client_message)
        sg.send(agent_message)
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        flash('Contract created but email notification failed.', 'warning')

@app.route('/sign_contract/<int:contract_id>', methods=['GET', 'POST'])
def sign_contract(contract_id):
    result = ContractManager.get_contract(contract_id)
    contract = result.data[0] if result.data else None
    signer_email = request.args.get('email', '')
    
    if not contract:
        flash('Contract not found', 'error')
        return redirect(url_for('index'))
    
    # Verify if the signer is authorized
    if signer_email not in [contract['agent_email'], contract['client_email']]:
        flash('Unauthorized to sign this contract', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        signature = request.form.get('signature')
        if not signature:
            flash('Signature is required', 'error')
            return redirect(url_for('sign_contract', contract_id=contract_id, email=signer_email))
        
        update_data = {}
        
        if signer_email == contract['agent_email']:
            update_data.update({
                'agent_signature': signature,
                'agent_signed_date': datetime.utcnow().isoformat(),
                'agent_status': 'signed'
            })
        elif signer_email == contract['client_email']:
            update_data.update({
                'client_signature': signature,
                'client_signed_date': datetime.utcnow().isoformat(),
                'client_status': 'signed'
            })
        
        if update_data:
            # Update overall status based on both signatures
            if (
                (contract['agent_status'] == 'signed' or 'agent_status' in update_data) and
                (contract['client_status'] == 'signed' or 'client_status' in update_data)
            ):
                update_data['status'] = 'completed'
            else:
                update_data['status'] = 'partially_signed'
            
            try:
                ContractManager.update_contract(contract_id, update_data)
                flash('Contract signed successfully!', 'success')
                return redirect(url_for('signature_confirmation'))
            except Exception as e:
                flash(f'Error updating contract: {str(e)}', 'error')
                return redirect(url_for('sign_contract', contract_id=contract_id, email=signer_email))
    
    return render_template('sign_contract.html', contract=contract, signer_email=signer_email)

@app.route('/signature_confirmation')
def signature_confirmation():
    return render_template('signature_confirmation.html')

@app.route('/view_contract/<int:contract_id>')
def view_contract(contract_id):
    result = ContractManager.get_contract(contract_id)
    contract = result.data[0] if result.data else None
    
    if not contract:
        flash('Contract not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('view_contract.html', contract=contract)

@app.route('/download_contract/<int:contract_id>')
def download_contract(contract_id):
    result = ContractManager.get_contract(contract_id)
    contract = result.data[0] if result.data else None
    
    if not contract or contract['status'] != 'completed':
        flash('Contract must be fully signed before downloading', 'error')
        return redirect(url_for('view_contract', contract_id=contract_id))
    
    # Convert signature data URLs to base64 images for PDF
    if contract['agent_signature']:
        contract['agent_signature'] = contract['agent_signature'].split(',')[1]
        contract['agent_signature'] = f"data:image/png;base64,{contract['agent_signature']}"
    
    if contract['client_signature']:
        contract['client_signature'] = contract['client_signature'].split(',')[1]
        contract['client_signature'] = f"data:image/png;base64,{contract['client_signature']}"
    
    # Convert string dates to datetime objects for proper formatting
    contract['created_at'] = datetime.fromisoformat(contract['created_at'])
    contract['start_date'] = datetime.fromisoformat(contract['start_date'])
    contract['end_date'] = datetime.fromisoformat(contract['end_date'])
    contract['agent_signed_date'] = datetime.fromisoformat(contract['agent_signed_date'])
    contract['client_signed_date'] = datetime.fromisoformat(contract['client_signed_date'])
    
    # Generate PDF
    html_content = render_template('contract_pdf.html', contract=contract)
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    filename = f"contract_{contract_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        pdf_file,
        download_name=filename,
        as_attachment=True,
        mimetype='application/pdf'
    )
# Add this after the existing imports
from forms import ContractForm
from flask import send_file

# Add this before the first route
@app.route('/')
def index():
    contracts = ContractManager.get_all_contracts()
    return render_template('index.html', contracts=contracts.data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)