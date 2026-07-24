-- Vyapar Sathi: day-to-day transactions
-- Run once: mysql -u root -p < database/schema.sql
-- Or: npm run db:init

CREATE DATABASE IF NOT EXISTS vyapar_sathi
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE vyapar_sathi;

CREATE TABLE IF NOT EXISTS transactions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  amount DECIMAL(15, 2) NOT NULL COMMENT 'Line amount (e.g. line total; optional qty * rate in notes)',
  quantity DECIMAL(12, 3) NULL DEFAULT NULL COMMENT 'Units (optional)',
  gst_amount DECIMAL(15, 2) NULL DEFAULT NULL,
  transaction_date DATE NOT NULL,
  category VARCHAR(128) NOT NULL,
  transaction_type VARCHAR(64) NOT NULL COMMENT 'Business kind: purchase, sales, rent, etc.',
  description VARCHAR(512) NULL DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_transactions_date (transaction_date),
  KEY idx_transactions_type (transaction_type),
  KEY idx_transactions_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
