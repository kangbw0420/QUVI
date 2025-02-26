#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
from decimal import Decimal
from typing import List, Dict, Any

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary modules
from utils.compute.main_compute import compute_fstring
from utils.compute.computer import compute_function, parse_function_params, safe_decimal
from utils.compute.formatter import should_use_decimals, format_number

# Sample data for testing list function with decimal values
sample_data = [
    {"avg_expense": 1233333.33, "avg_income": 2345678.90, "profit_margin": 12.34},
    {"avg_expense": 1100000.00, "avg_income": 2200000.00, "profit_margin": 10.50},
    {"avg_expense": 1300000.00, "avg_income": 2500000.00, "profit_margin": 14.75},
]

column_list = ["avg_expense", "avg_income", "profit_margin"]

def test_list_function_single_value():
    """Test the list function with a single decimal value"""
    print("\n=== Test 1: list function with a single decimal value ===")
    
    # Create a test data with only one row
    one_row_data = [sample_data[0]]
    
    # Test cases for different decimal values
    test_fstrings = [
        '지출 금액: {list(avg_expense)}원',
        '수입 금액: {list(avg_income)}원',
        '수익률: {list(profit_margin)}%'
    ]
    
    for fstring in test_fstrings:
        print(f"\nFstring: {fstring}")
        
        # Process the expression
        import re
        pattern = r'\{([^}]+)\}'
        match = re.search(pattern, fstring)
        if match:
            expr = match.group(1)
            func_match = re.match(r'(\w+(?:\.\w+)?)\((.*?)\)', expr)
            if func_match:
                func_name, param_str = func_match.groups()
                params = parse_function_params(param_str)
                
                # Get the raw value from the data
                param = params[0]
                raw_value = one_row_data[0][param]
                print(f"Raw value from data: {raw_value} (Type: {type(raw_value)})")
                
                # Compute using the list function
                value = compute_function(func_name, params, one_row_data, column_list)
                print(f"Value after compute_function: {value} (Type: {type(value)})")
                
                # Check if this value would use decimals in formatting
                use_decimals = should_use_decimals(param, func_name, params)
                print(f"Should use decimals for {param}: {use_decimals}")
        
        # Compute the entire fstring
        result = compute_fstring(fstring, one_row_data, column_list)
        print(f"Final result: {result}")

def test_list_function_multiple_values():
    """Test the list function with multiple decimal values"""
    print("\n=== Test 2: list function with multiple decimal values ===")
    
    # Test cases for different decimal values with all rows
    test_fstrings = [
        '지출 금액 목록: {list(avg_expense)}원',
        '수입 금액 목록: {list(avg_income)}원',
        '수익률 목록: {list(profit_margin)}%'
    ]
    
    for fstring in test_fstrings:
        print(f"\nFstring: {fstring}")
        
        # Process the expression
        import re
        pattern = r'\{([^}]+)\}'
        match = re.search(pattern, fstring)
        if match:
            expr = match.group(1)
            func_match = re.match(r'(\w+(?:\.\w+)?)\((.*?)\)', expr)
            if func_match:
                func_name, param_str = func_match.groups()
                params = parse_function_params(param_str)
                
                # Show raw values from the data
                param = params[0]
                raw_values = [row[param] for row in sample_data]
                print(f"Raw values from data: {raw_values}")
                
                # Convert to Decimal to see how they would be processed
                decimal_values = [safe_decimal(val) for val in raw_values]
                print(f"After conversion to Decimal: {decimal_values}")
                
                # Compute using the list function
                value = compute_function(func_name, params, sample_data, column_list)
                print(f"Value after compute_function: {value} (Type: {type(value)})")
        
        # Compute the entire fstring
        result = compute_fstring(fstring, sample_data, column_list)
        print(f"Final result: {result}")

def test_list_function_in_calculation():
    """Test the list function used in a mathematical expression"""
    print("\n=== Test 3: list function in a mathematical calculation ===")
    
    # Test cases where list function is part of a calculation
    test_fstrings = [
        '평균 수익률: {average(list(profit_margin))}%',
        '총 지출: {sum(list(avg_expense))}원',
        '평균 수입: {average(list(avg_income))}원'
    ]
    
    for fstring in test_fstrings:
        print(f"\nFstring: {fstring}")
        
        # Let's try to manually trace through the computation
        import re
        pattern = r'\{([^}]+)\}'
        match = re.search(pattern, fstring)
        if match:
            expr = match.group(1)
            print(f"Expression: {expr}")
            
            # Extract outer function and inner function
            outer_match = re.match(r'(\w+)\((.*)\)', expr)
            if outer_match:
                outer_func, inner_expr = outer_match.groups()
                print(f"Outer function: {outer_func}, Inner expression: {inner_expr}")
                
                inner_match = re.match(r'(\w+)\((.*)\)', inner_expr)
                if inner_match:
                    inner_func, inner_param = inner_match.groups()
                    print(f"Inner function: {inner_func}, Inner parameter: {inner_param}")
                    
                    # What would the inner function return?
                    inner_value = compute_function(inner_func, [inner_param], sample_data, column_list)
                    print(f"Inner function result: {inner_value} (Type: {type(inner_value)})")
                    
                    # Could we calculate the outer function manually?
                    if isinstance(inner_value, list) or isinstance(inner_value, str) and ',' in inner_value:
                        print("Inner function returned multiple values, cannot directly compute outer function")
                    else:
                        # For demonstration purposes, try computing the outer function
                        try:
                            if outer_func == 'average':
                                print("Computing average...")
                                # For single values, average is just the value
                                print(f"Result would be: {inner_value}")
                            elif outer_func == 'sum':
                                print("Computing sum...")
                                # For single values, sum is just the value
                                print(f"Result would be: {inner_value}")
                        except Exception as e:
                            print(f"Error in manual computation: {e}")
        
        # Compute the entire fstring
        try:
            result = compute_fstring(fstring, sample_data, column_list)
            print(f"Final result: {result}")
        except Exception as e:
            print(f"Error in compute_fstring: {e}")

def test_list_function_with_currency():
    """Test the list function with currency columns"""
    print("\n=== Test 4: list function with currency columns ===")
    
    # Add some currency columns to our data
    currency_data = []
    for row in sample_data:
        new_row = row.copy()
        new_row["USD_expense"] = row["avg_expense"] / 1300  # Hypothetical exchange rate
        new_row["EUR_income"] = row["avg_income"] / 1400  # Hypothetical exchange rate
        currency_data.append(new_row)
    
    # Update column list
    currency_columns = column_list + ["USD_expense", "EUR_income"]
    
    # Test cases for currency columns
    test_fstrings = [
        '달러 지출: {list(USD_expense)}$',
        '유로 수입: {list(EUR_income)}€',
        '달러 평균 지출: {average(USD_expense)}$',
        '유로 평균 수입: {average(EUR_income)}€'
    ]
    
    for fstring in test_fstrings:
        print(f"\nFstring: {fstring}")
        
        # Process the expression
        import re
        pattern = r'\{([^}]+)\}'
        match = re.search(pattern, fstring)
        if match:
            expr = match.group(1)
            func_match = re.match(r'(\w+(?:\.\w+)?)\((.*?)\)', expr)
            if func_match:
                func_name, param_str = func_match.groups()
                params = parse_function_params(param_str)
                
                # Check if this would use decimals in formatting
                param = params[0]
                use_decimals = should_use_decimals(param, func_name, params)
                print(f"Should use decimals for {param} with {func_name}: {use_decimals}")
                
                # Compute the function
                value = compute_function(func_name, params, currency_data, currency_columns)
                print(f"Value after compute_function: {value} (Type: {type(value)})")
                
                # Format the value directly
                formatted = format_number(value, param, func_name, params)
                print(f"Directly formatted value: {formatted}")
        
        # Compute the entire fstring
        result = compute_fstring(fstring, currency_data, currency_columns)
        print(f"Final result: {result}")

if __name__ == "__main__":
    print("Starting list function tests...")

    test_list_function_with_currency()
    print("\nTests completed")