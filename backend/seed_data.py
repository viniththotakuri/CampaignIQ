"""
Database Seeder for CampaignIQ
PS-8 Banking Call Center Intelligence System

Seeds:
1. Team Leader and Calling Agent accounts (with securely hashed passwords)
2. Realistic banking customers matching the UCI Bank Marketing benchmark
3. Ensures idempotency: safely skips existing records without duplicating
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from database import SessionLocal, init_db
from models import User, Customer, Campaign


# --------------------------------------------------
# DEFAULT CALL CENTER TEAM USERS
# --------------------------------------------------

DEFAULT_USERS = [
    {
        "username": "leader",
        "password": "leader123",
        "full_name": "Vikram Malhotra",
        "role": "leader",
        "email": "vikram.malhotra@bank.com"
    },
    {
        "username": "agent1",
        "password": "agent123",
        "full_name": "Rahul Sharma",
        "role": "agent",
        "email": "rahul.sharma@bank.com"
    },
    {
        "username": "agent2",
        "password": "agent123",
        "full_name": "Priya Patel",
        "role": "agent",
        "email": "priya.patel@bank.com"
    },
    {
        "username": "agent3",
        "password": "agent123",
        "full_name": "Amit Verma",
        "role": "agent",
        "email": "amit.verma@bank.com"
    }
]


# --------------------------------------------------
# REALISTIC BENCHMARK CUSTOMERS (UCI Bank Marketing)
# --------------------------------------------------

SAMPLE_CUSTOMERS = [
    {
        "name": "Aarav Patel",
        "phone": "+91 98201 11201",
        "age": 56,
        "job": "housemaid",
        "marital": "married",
        "education": "basic.4y",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "telephone",
        "month": "may",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.857,
        "nr_employed": 5191.0
    },
    {
        "name": "Diya Sharma",
        "phone": "+91 98201 11202",
        "age": 37,
        "job": "services",
        "marital": "married",
        "education": "high.school",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "telephone",
        "month": "may",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.857,
        "nr_employed": 5191.0
    },
    {
        "name": "Rohan Gupta",
        "phone": "+91 98201 11203",
        "age": 41,
        "job": "blue-collar",
        "marital": "married",
        "education": "basic.4y",
        "default": "unknown",
        "housing": "yes",
        "loan": "no",
        "contact": "telephone",
        "month": "may",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.857,
        "nr_employed": 5191.0
    },
    {
        "name": "Sneha Iyer",
        "phone": "+91 98201 11204",
        "age": 32,
        "job": "admin.",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "aug",
        "day_of_week": "thu",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.444,
        "cons_conf_idx": -36.1,
        "euribor3m": 4.963,
        "nr_employed": 5228.1
    },
    {
        "name": "Kavita Reddy",
        "phone": "+91 98201 11205",
        "age": 59,
        "job": "retired",
        "marital": "divorced",
        "education": "basic.4y",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "jul",
        "day_of_week": "tue",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.918,
        "cons_conf_idx": -42.7,
        "euribor3m": 4.961,
        "nr_employed": 5228.1
    },
    {
        "name": "Arjun Nair",
        "phone": "+91 98201 11206",
        "age": 29,
        "job": "technician",
        "marital": "single",
        "education": "professional.course",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "jul",
        "day_of_week": "fri",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.918,
        "cons_conf_idx": -42.7,
        "euribor3m": 4.957,
        "nr_employed": 5228.1
    },
    {
        "name": "Ananya Joshi",
        "phone": "+91 98201 11207",
        "age": 28,
        "job": "student",
        "marital": "single",
        "education": "high.school",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "apr",
        "day_of_week": "thu",
        "campaign": 1,
        "pdays": 3,
        "previous": 2,
        "poutcome": "success",
        "emp_var_rate": -1.8,
        "cons_price_idx": 93.075,
        "cons_conf_idx": -47.1,
        "euribor3m": 1.405,
        "nr_employed": 5099.1
    },
    {
        "name": "Vikram Singhania",
        "phone": "+91 98201 11208",
        "age": 62,
        "job": "retired",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "mar",
        "day_of_week": "wed",
        "campaign": 1,
        "pdays": 6,
        "previous": 1,
        "poutcome": "success",
        "emp_var_rate": -1.8,
        "cons_price_idx": 92.843,
        "cons_conf_idx": -50.0,
        "euribor3m": 1.811,
        "nr_employed": 5099.1
    },
    {
        "name": "Meera Sen",
        "phone": "+91 98201 11209",
        "age": 35,
        "job": "management",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "jun",
        "day_of_week": "tue",
        "campaign": 3,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": -2.9,
        "cons_price_idx": 92.963,
        "cons_conf_idx": -40.8,
        "euribor3m": 1.266,
        "nr_employed": 5076.2
    },
    {
        "name": "Naveen Rao",
        "phone": "+91 98201 11210",
        "age": 45,
        "job": "entrepreneur",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "yes",
        "contact": "cellular",
        "month": "aug",
        "day_of_week": "mon",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.444,
        "cons_conf_idx": -36.1,
        "euribor3m": 4.965,
        "nr_employed": 5228.1
    },
    {
        "name": "Pooja Hegde",
        "phone": "+91 98201 11211",
        "age": 24,
        "job": "student",
        "marital": "single",
        "education": "high.school",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "oct",
        "day_of_week": "tue",
        "campaign": 1,
        "pdays": 4,
        "previous": 1,
        "poutcome": "success",
        "emp_var_rate": -3.4,
        "cons_price_idx": 92.431,
        "cons_conf_idx": -26.9,
        "euribor3m": 0.742,
        "nr_employed": 5017.5
    },
    {
        "name": "Karthik Sundaram",
        "phone": "+91 98201 11212",
        "age": 48,
        "job": "technician",
        "marital": "married",
        "education": "professional.course",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "nov",
        "day_of_week": "wed",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": -0.1,
        "cons_price_idx": 93.2,
        "cons_conf_idx": -42.0,
        "euribor3m": 4.076,
        "nr_employed": 5195.8
    },
    {
        "name": "Shweta Deshmukh",
        "phone": "+91 98201 11213",
        "age": 31,
        "job": "admin.",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "may",
        "day_of_week": "thu",
        "campaign": 1,
        "pdays": 999,
        "previous": 1,
        "poutcome": "failure",
        "emp_var_rate": -1.8,
        "cons_price_idx": 92.893,
        "cons_conf_idx": -46.2,
        "euribor3m": 1.281,
        "nr_employed": 5099.1
    },
    {
        "name": "Girish Pillai",
        "phone": "+91 98201 11214",
        "age": 53,
        "job": "blue-collar",
        "marital": "married",
        "education": "basic.9y",
        "default": "unknown",
        "housing": "no",
        "loan": "no",
        "contact": "telephone",
        "month": "jun",
        "day_of_week": "fri",
        "campaign": 4,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 94.465,
        "cons_conf_idx": -41.8,
        "euribor3m": 4.959,
        "nr_employed": 5228.1
    },
    {
        "name": "Deepika Bhatt",
        "phone": "+91 98201 11215",
        "age": 39,
        "job": "management",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "aug",
        "day_of_week": "fri",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.444,
        "cons_conf_idx": -36.1,
        "euribor3m": 4.964,
        "nr_employed": 5228.1
    },
    {
        "name": "Manish Kulkarni",
        "phone": "+91 98201 11216",
        "age": 70,
        "job": "retired",
        "marital": "married",
        "education": "basic.4y",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "oct",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": -3.4,
        "cons_price_idx": 92.431,
        "cons_conf_idx": -26.9,
        "euribor3m": 0.722,
        "nr_employed": 5017.5
    },
    {
        "name": "Ritika Bannerjee",
        "phone": "+91 98201 11217",
        "age": 27,
        "job": "admin.",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "yes",
        "contact": "cellular",
        "month": "jul",
        "day_of_week": "mon",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.918,
        "cons_conf_idx": -42.7,
        "euribor3m": 4.960,
        "nr_employed": 5228.1
    },
    {
        "name": "Sunil Nambiar",
        "phone": "+91 98201 11218",
        "age": 44,
        "job": "self-employed",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "may",
        "day_of_week": "tue",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": -1.8,
        "cons_price_idx": 92.893,
        "cons_conf_idx": -46.2,
        "euribor3m": 1.291,
        "nr_employed": 5099.1
    },
    {
        "name": "Tanvi Kapoor",
        "phone": "+91 98201 11219",
        "age": 36,
        "job": "services",
        "marital": "single",
        "education": "high.school",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "telephone",
        "month": "may",
        "day_of_week": "wed",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.856,
        "nr_employed": 5191.0
    },
    {
        "name": "Abhishek Chawla",
        "phone": "+91 98201 11220",
        "age": 51,
        "job": "blue-collar",
        "marital": "married",
        "education": "basic.9y",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "nov",
        "day_of_week": "thu",
        "campaign": 1,
        "pdays": 999,
        "previous": 1,
        "poutcome": "failure",
        "emp_var_rate": -0.1,
        "cons_price_idx": 93.2,
        "cons_conf_idx": -42.0,
        "euribor3m": 4.076,
        "nr_employed": 5195.8
    },
    {
        "name": "Neha Agarwal",
        "phone": "+91 98201 11221",
        "age": 25,
        "job": "student",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "aug",
        "day_of_week": "wed",
        "campaign": 1,
        "pdays": 6,
        "previous": 2,
        "poutcome": "success",
        "emp_var_rate": -1.7,
        "cons_price_idx": 94.027,
        "cons_conf_idx": -38.3,
        "euribor3m": 0.899,
        "nr_employed": 4991.6
    },
    {
        "name": "Harish Menon",
        "phone": "+91 98201 11222",
        "age": 64,
        "job": "retired",
        "marital": "married",
        "education": "high.school",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "sep",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 3,
        "previous": 2,
        "poutcome": "success",
        "emp_var_rate": -1.1,
        "cons_price_idx": 94.199,
        "cons_conf_idx": -37.5,
        "euribor3m": 0.879,
        "nr_employed": 4963.6
    },
    {
        "name": "Bhavna Trivedi",
        "phone": "+91 98201 11223",
        "age": 42,
        "job": "admin.",
        "marital": "divorced",
        "education": "high.school",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "may",
        "day_of_week": "fri",
        "campaign": 3,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": -1.8,
        "cons_price_idx": 92.893,
        "cons_conf_idx": -46.2,
        "euribor3m": 1.313,
        "nr_employed": 5099.1
    },
    {
        "name": "Siddharth Jain",
        "phone": "+91 98201 11224",
        "age": 33,
        "job": "technician",
        "marital": "married",
        "education": "professional.course",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "jul",
        "day_of_week": "wed",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.918,
        "cons_conf_idx": -42.7,
        "euribor3m": 4.963,
        "nr_employed": 5228.1
    },
    {
        "name": "Pallavi Saxena",
        "phone": "+91 98201 11225",
        "age": 47,
        "job": "management",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "aug",
        "day_of_week": "tue",
        "campaign": 2,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.4,
        "cons_price_idx": 93.444,
        "cons_conf_idx": -36.1,
        "euribor3m": 4.963,
        "nr_employed": 5228.1
    }
]


def seed_database():
    """
    Initializes tables and seeds users and benchmark customers.
    Safe to run repeatedly without duplicate records.
    """
    init_db()
    db = SessionLocal()

    print("\n========== SEEDING DATABASE ==========")

    try:
        # 1. Seed Call Center Users
        users_added = 0
        for user_data in DEFAULT_USERS:
            existing_user = db.query(User).filter_by(username=user_data["username"]).first()
            if not existing_user:
                new_user = User(
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    email=user_data["email"],
                    is_active=True
                )
                new_user.set_password(user_data["password"])
                db.add(new_user)
                users_added += 1
                print(f"  [+] Added User: {user_data['username']} ({user_data['role']})")
            else:
                print(f"  [.] User already exists: {user_data['username']}")

        db.commit()

        # 2. Seed Benchmark Customers
        customers_added = 0
        for cust_data in SAMPLE_CUSTOMERS:
            existing_cust = db.query(Customer).filter_by(phone=cust_data["phone"]).first()
            if not existing_cust:
                new_cust = Customer(
                    name=cust_data["name"],
                    phone=cust_data["phone"],
                    age=cust_data["age"],
                    job=cust_data["job"],
                    marital=cust_data["marital"],
                    education=cust_data["education"],
                    default=cust_data["default"],
                    housing=cust_data["housing"],
                    loan=cust_data["loan"],
                    contact=cust_data["contact"],
                    month=cust_data["month"],
                    day_of_week=cust_data["day_of_week"],
                    campaign=cust_data["campaign"],
                    pdays=cust_data["pdays"],
                    previous=cust_data["previous"],
                    poutcome=cust_data["poutcome"],
                    emp_var_rate=cust_data["emp_var_rate"],
                    cons_price_idx=cust_data["cons_price_idx"],
                    cons_conf_idx=cust_data["cons_conf_idx"],
                    euribor3m=cust_data["euribor3m"],
                    nr_employed=cust_data["nr_employed"]
                )
                db.add(new_cust)
                customers_added += 1
            else:
                pass  # Skip duplicate

        db.commit()
        print(f"  [+] Added {customers_added} benchmark customers (Total in DB: {db.query(Customer).count()})")

        print("========== SEEDING COMPLETE ==========\n")
        return {
            "users_added": users_added,
            "total_users": db.query(User).count(),
            "customers_added": customers_added,
            "total_customers": db.query(Customer).count()
        }

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
