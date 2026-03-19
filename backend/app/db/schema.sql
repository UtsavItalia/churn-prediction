CREATE TABLE customers
(
    customer_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    country VARCHAR(100),
    industry VARCHAR(100),
    company_size VARCHAR(50),
    contract_type VARCHAR(50),
    plan_tier VARCHAR(50),
    acquisition_channel VARCHAR(100),
    churned BOOLEAN DEFAULT FALSE,
    churn_date TIMESTAMP NULL,
    churn_reason VARCHAR(200) NULL
);

CREATE TABLE monthly_usage
(
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    month_year DATE NOT NULL,
    active_users INT DEFAULT 0,
    feature_adoption_score FLOAT,
    sessions_count INT DEFAULT 0,
    avg_session_duration_mins FLOAT,
    data_processed_gb FLOAT,
    api_calls INT DEFAULT 0,
    UNIQUE(customer_id, month_year)
);

CREATE TABLE support_tickets
(
    ticket_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP NULL,
    category VARCHAR(100),
    priority VARCHAR(50),
    satisfaction_score INT
);

CREATE TABLE billing_history
(
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    billing_date TIMESTAMP NOT NULL,
    amount_due FLOAT NOT NULL,
    amount_paid FLOAT NOT NULL,
    payment_status VARCHAR(50),
    days_to_payment INT
);
CREATE TABLE churn_predictions
(
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    predicted_at TIMESTAMP DEFAULT NOW(),
    churn_probability FLOAT NOT NULL,
    risk_segment VARCHAR(50),
    model_version VARCHAR(50),
    top_features JSONB
);
