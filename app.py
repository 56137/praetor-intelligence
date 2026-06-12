@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload    = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return jsonify({"error": "Payload inválido"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Firma inválida"}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')

        if customer_email and os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r') as f:
                leads = json.load(f)

            matching = [l for l in leads if l.get('email') == customer_email]
            if matching:
                last_lead = matching[-1]
                domain = last_lead['domain']
                safe_name = domain.replace('.', '_').replace('/', '_')
                pdf_filename = f'REPORT_{safe_name}.pdf'

                last_lead['status'] = 'paid'
                last_lead['pdf_file'] = pdf_filename
                with open(LEADS_FILE, 'w') as f:
                    json.dump(leads, f, indent=2)

    return jsonify({"status": "ok"}), 200
