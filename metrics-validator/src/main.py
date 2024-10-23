from process.cpu_time.validate import ValidateCPUTime

# stress load proportion assigned prior to sum?
if __name__ == "__main__":
    v = ValidateCPUTime(
        stresser_timeout=60,
        stress_load=10
    )
    result = v.validate()
    print(result.mae)
    print(result.mape)
    