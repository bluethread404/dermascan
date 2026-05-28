CREATE DATABASE skin_cancer_db1;
USE skin_cancer_db1;

CREATE TABLE users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(500)
);
CREATE TABLE patients(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    result VARCHAR(20),
    probability FLOAT,
    image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users(username,password) VALUES('admin','1234');
CREATE TABLE symptom_quiz (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id       INT,
    growth            VARCHAR(20),
    itching           VARCHAR(20),
    bleeding          VARCHAR(10),
    pain              VARCHAR(20),
    color_change      VARCHAR(20),
    irregular_border  VARCHAR(20),
    systemic_symptoms VARCHAR(10),
    risk_score        INT,
    risk_level        VARCHAR(20),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
UPDATE users
SET password = 'scrypt:32768:8:1$al3yIaXTNpuHPwK6$2fb72864f115f89e12c0e026a4c43054760e46cd1e0174015ba5d3804fac5eae7c06cc2f6039311896dfdbf67ffe5ee22c8a346479fa4761b47c889fd49eb2e2'
WHERE username = 'admin';
ALTER TABLE users ADD role VARCHAR(20) DEFAULT 'user';