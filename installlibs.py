import subprocess

def install_libraries():
    libraries = [
        'tkinter',
        'requests',
        'transformers',
        'sympy'
        # Add more libraries as needed
    ]
    
    for lib in libraries:
        subprocess.call(['pip', 'install', lib])

if __name__ == "__main__":
    install_libraries()
