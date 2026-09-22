import sys
from python_services.calculator_humanizer.calc_processor import CalcHumanizerModule

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"CALC MODULE OUTPUT:\n{CalcHumanizerModule().process(query)}")
    else:
        print("Usage: python run_calc.py <metric, value>")
        print("Example: python run_calc.py profit, 34000")
