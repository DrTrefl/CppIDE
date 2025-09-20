import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import sys
from pathlib import Path
import tempfile
import queue
import time

class CppCompilerIDE:
    def __init__(self, root):
        self.root = root
        self.root.iconbitmap('../assets/icon.ico')
        self.root.title("C++ IDE")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')
        
        self.current_file = None
        self.process = None
        self.output_queue = queue.Queue()
        
        self.setup_styles()
        
        self.create_menu()
        self.create_toolbar()
        self.create_main_layout()
        self.create_status_bar()
        
        self.load_sample_code()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        select_color = '#404040'
        
        style.configure('Custom.TFrame', background=bg_color)
        style.configure('Custom.TLabel', background=bg_color, foreground=fg_color)
        style.configure('Custom.TButton', background='#404040', foreground=fg_color)
        
    def create_menu(self):
        menubar = tk.Menu(self.root, bg='#2b2b2b', fg='white')
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        build_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Build", menu=build_menu)
        build_menu.add_command(label="Compile", command=self.compile_code, accelerator="F5")
        build_menu.add_command(label="Compile and Run", command=self.compile_and_run, accelerator="F6")
        build_menu.add_command(label="Run Only", command=self.run_code, accelerator="F7")
        build_menu.add_separator()
        build_menu.add_command(label="Clear", command=self.clean_build)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.compile_code())
        self.root.bind('<F6>', lambda e: self.compile_and_run())
        self.root.bind('<F7>', lambda e: self.run_code())
        
    def create_toolbar(self):
        toolbar_frame = tk.Frame(self.root, bg='#404040', height=40)
        toolbar_frame.pack(fill='x', padx=2, pady=2)
        toolbar_frame.pack_propagate(False)
        
        buttons = [
            ("New", "New", self.new_file),
            ("Open", "Open", self.open_file),
            ("Save", "Save", self.save_file),
            ("|", "", None),
            ("Compile", "Compile", self.compile_code),
            ("Compile and Run", "Compile and Run", self.compile_and_run),
            ("Run", "Run", self.run_code),
            ("Clean", "Clean", self.clean_build),
            ("|", "", None),
            ("Stop", "Stop", self.stop_execution)
        ]
        
        for text, tooltip, command in buttons:
            if text == "|":
                separator = tk.Frame(toolbar_frame, width=2, bg='#606060')
                separator.pack(side='left', fill='y', padx=5, pady=5)
            else:
                btn = tk.Button(toolbar_frame, text=text, command=command,
                              bg='#505050', fg='white', border=0, padx=10, pady=5)
                btn.pack(side='left', padx=2)
                if tooltip:
                    self.create_tooltip(btn, tooltip)
    
    def create_tooltip(self, widget, text):
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, bg='#404040', fg='white', 
                           relief='solid', borderwidth=1, padx=5, pady=2)
            label.pack()
            widget.tooltip = tooltip
            
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
    def create_main_layout(self):
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        paned = tk.PanedWindow(main_frame, orient='horizontal', bg='#2b2b2b', 
                              sashwidth=5, relief='flat')
        paned.pack(fill='both', expand=True)
        
        editor_frame = tk.Frame(paned, bg='#2b2b2b')
        paned.add(editor_frame, width=800)
        
        editor_label = tk.Label(editor_frame, text="C++ Code Editor", 
                               bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        editor_label.pack(anchor='w', padx=5, pady=5)
        
        self.code_editor = scrolledtext.ScrolledText(
            editor_frame, 
            bg='#1e1e1e', 
            fg='#d4d4d4',
            insertbackground='white',
            selectbackground='#264f78',
            font=('Consolas', 12),
            wrap='none',
            undo=True,
            maxundo=50
        )
        self.code_editor.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.setup_syntax_highlighting()
        
        right_frame = tk.Frame(paned, bg='#2b2b2b')
        paned.add(right_frame, width=600)
        
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        output_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(output_frame, text='Compilation Result')
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 10),
            state='disabled'
        )
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        terminal_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(terminal_frame, text='Terminal')
        
        self.terminal_output = scrolledtext.ScrolledText(
            terminal_frame,
            bg='#0c0c0c',
            fg='#00ff00',
            font=('Consolas', 10),
            state='disabled'
        )
        self.terminal_output.pack(fill='both', expand=True, padx=5, pady=(5,0))
        
        terminal_input_frame = tk.Frame(terminal_frame, bg='#2b2b2b')
        terminal_input_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(terminal_input_frame, text="$", bg='#2b2b2b', fg='#00ff00', 
                font=('Consolas', 10)).pack(side='left')
        
        self.terminal_input = tk.Entry(terminal_input_frame, bg='#1e1e1e', 
                                     fg='#00ff00', font=('Consolas', 10),
                                     insertbackground='#00ff00')
        self.terminal_input.pack(side='left', fill='x', expand=True, padx=5)
        self.terminal_input.bind('<Return>', self.execute_terminal_command)
        
        settings_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(settings_frame, text='Settings')
        
        self.create_compiler_settings(settings_frame)
        
    def setup_syntax_highlighting(self):
        self.code_editor.tag_configure("keyword", foreground="#569cd6")
        self.code_editor.tag_configure("string", foreground="#ce9178")
        self.code_editor.tag_configure("comment", foreground="#6a9955")
        self.code_editor.tag_configure("preprocessor", foreground="#9cdcfe")
        self.code_editor.tag_configure("number", foreground="#b5cea8")
        
        self.keywords = {
            'int', 'char', 'float', 'double', 'bool', 'void', 'auto',
            'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'default',
            'break', 'continue', 'return', 'class', 'struct', 'namespace',
            'using', 'const', 'static', 'extern', 'inline', 'virtual',
            'public', 'private', 'protected', 'try', 'catch', 'throw',
            'new', 'delete', 'sizeof', 'typedef', 'template', 'typename'
        }
        
        self.code_editor.bind('<KeyRelease>', self.update_syntax_highlighting)
        
    def update_syntax_highlighting(self, event=None):
        content = self.code_editor.get(1.0, tk.END)
        
        for tag in ["keyword", "string", "comment", "preprocessor", "number"]:
            self.code_editor.tag_delete(tag)
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if '//' in line:
                start = line.find('//')
                self.code_editor.tag_add("comment", f"{line_num}.{start}", f"{line_num}.end")
            
            if line.strip().startswith('#'):
                self.code_editor.tag_add("preprocessor", f"{line_num}.0", f"{line_num}.end")
            
            in_string = False
            i = 0
            while i < len(line):
                if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        start = i
                        in_string = True
                    else:
                        self.code_editor.tag_add("string", f"{line_num}.{start}", f"{line_num}.{i+1}")
                        in_string = False
                i += 1
            
            words = line.split()
            col = 0
            for word in words:
                clean_word = ''.join(c for c in word if c.isalnum() or c == '_')
                if clean_word in self.keywords:
                    start_pos = line.find(word, col)
                    if start_pos != -1:
                        self.code_editor.tag_add("keyword", f"{line_num}.{start_pos}", 
                                               f"{line_num}.{start_pos + len(clean_word)}")
                        col = start_pos + len(word)
        
    def create_compiler_settings(self, parent):
        settings_scroll = scrolledtext.ScrolledText(parent, bg='#2b2b2b', height=10)
        settings_scroll.pack(fill='both', expand=True, padx=10, pady=10)
        
        settings_content = tk.Frame(parent, bg='#2b2b2b')
        settings_content.pack(fill='x', padx=10, pady=5)
        
        tk.Label(settings_content, text="Compiler:", bg='#2b2b2b', fg='white').grid(row=0, column=0, sticky='w', pady=2)
        self.compiler_var = tk.StringVar(value="g++")
        compiler_combo = ttk.Combobox(settings_content, textvariable=self.compiler_var, 
                                    values=["g++", "clang++", "cl"])
        compiler_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(settings_content, text="Flags:", bg='#2b2b2b', fg='white').grid(row=1, column=0, sticky='w', pady=2)
        self.flags_var = tk.StringVar(value="-std=c++17 -O2 -Wall")
        flags_entry = tk.Entry(settings_content, textvariable=self.flags_var, bg='#404040', fg='white')
        flags_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(settings_content, text="Standard:", bg='#2b2b2b', fg='white').grid(row=2, column=0, sticky='w', pady=2)
        self.std_var = tk.StringVar(value="c++17")
        std_combo = ttk.Combobox(settings_content, textvariable=self.std_var,
                               values=["c++11", "c++14", "c++17", "c++20", "c++23"])
        std_combo.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        settings_content.columnconfigure(1, weight=1)
        
    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg='#404040', height=25)
        self.status_bar.pack(fill='x', side='bottom')
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="Done", 
                                   bg='#404040', fg='white', anchor='w')
        self.status_label.pack(side='left', padx=10)
        
        self.file_info = tk.Label(self.status_bar, text="New File", 
                                bg='#404040', fg='white', anchor='e')
        self.file_info.pack(side='right', padx=10)
        
    def load_sample_code(self):
        sample_code = '''#include <iostream>
using namespace std;

int main() {
    cout << "Hello World" << endl;
    return 0;
}'''
        self.code_editor.insert(1.0, sample_code)
        self.update_syntax_highlighting()
        
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()
        
    def append_output(self, text, color="white"):
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, text + '\n')
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')
        
    def append_terminal(self, text, color="#00ff00"):
        self.terminal_output.config(state='normal')
        self.terminal_output.insert(tk.END, text + '\n')
        self.terminal_output.see(tk.END)
        self.terminal_output.config(state='disabled')
        
    def clear_output(self):
        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state='disabled')
        
    def new_file(self):
        if messagebox.askyesno("New File", "Would you like to create a new file?"):
            self.code_editor.delete(1.0, tk.END)
            self.current_file = None
            self.file_info.config(text="New File")
            self.update_status("A new file has been created")
            
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open C++ File",
            filetypes=[("C++ files", "*.cpp *.cxx *.cc"), ("C files", "*.c"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.code_editor.delete(1.0, tk.END)
                    self.code_editor.insert(1.0, content)
                    self.current_file = file_path
                    self.file_info.config(text=os.path.basename(file_path))
                    self.update_status(f"Opened: {file_path}")
                    self.update_syntax_highlighting()
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file: {e}")
                
    def save_file(self):
        if self.current_file:
            try:
                content = self.code_editor.get(1.0, tk.END + '-1c')
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                self.update_status(f"Saved: {self.current_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Cannot save file: {e}")
        else:
            self.save_as_file()
            
    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".cpp",
            filetypes=[("C++ files", "*.cpp"), ("C files", "*.c"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                content = self.code_editor.get(1.0, tk.END + '-1c')
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                self.current_file = file_path
                self.file_info.config(text=os.path.basename(file_path))
                self.update_status(f"Saved as: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Cannot save file: {e}")
                
    def compile_code(self):
        self.clear_output()
        self.update_status("Compiling...")
        self.notebook.select(0)
        
        code = self.code_editor.get(1.0, tk.END + '-1c')
        
        if not code.strip():
            self.append_output("No code to compile!", "red")
            self.update_status("Error: No code")
            return False
            
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as temp_file:
                temp_file.write(code)
                self.temp_source = temp_file.name
                
            if sys.platform == "win32":
                self.temp_executable = self.temp_source.replace('.cpp', '.exe')
            else:
                self.temp_executable = self.temp_source.replace('.cpp', '')
                
            compiler = self.compiler_var.get()
            flags = self.flags_var.get()
            std = f"-std={self.std_var.get()}"
            
            compile_cmd = [compiler, std] + flags.split() + [self.temp_source, '-o', self.temp_executable]
            
            self.append_output(f"Compiling: {' '.join(compile_cmd)}")
            
            def compile_thread():
                try:
                    result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        self.append_output("Compilation completed successfully!")
                        if result.stdout:
                            self.append_output(f"Output: {result.stdout}")
                        self.update_status("Compilation completed successfully")
                        return True
                    else:
                        self.append_output("Compilation Errors:")
                        if result.stderr:
                            self.append_output(result.stderr)
                        if result.stdout:
                            self.append_output(result.stdout)
                        self.update_status("Compilation Error")
                        return False
                        
                except subprocess.TimeoutExpired:
                    self.append_output("Compilation exceeded the time limit (30 seconds)")
                    self.update_status("Compilation - timeout")
                    return False
                except FileNotFoundError:
                    self.append_output(f"Compiler {compiler} Not found!")
                    self.update_status("Error: No compiler")
                    return False
                except Exception as e:
                    self.append_output(f"Compilation Error: {e}")
                    self.update_status("Compilation Error")
                    return False
                    
            thread = threading.Thread(target=compile_thread)
            thread.daemon = True
            thread.start()
            
            return True
            
        except Exception as e:
            self.append_output(f"Error during compilation setup: {e}")
            self.update_status("Setup Error")
            return False
            
    def run_code(self):
        if not hasattr(self, 'temp_executable') or not os.path.exists(self.temp_executable):
            self.append_output("No compiled file! Please compile the code first.")
            return
            
        self.notebook.select(1)
        self.update_status("Running the program...")
        
        def run_thread():
            try:
                self.append_terminal(f"Running: {os.path.basename(self.temp_executable)}")
                self.append_terminal("_" * 50)
                
                self.process = subprocess.Popen(
                    [self.temp_executable],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=0
                )
                
                while True:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output:
                        self.append_terminal(output.rstrip())
                        
                return_code = self.process.poll()
                self.append_terminal("_" * 50)
                self.append_terminal(f"Program finished with code: {return_code}")
                
                if return_code == 0:
                    self.update_status("Program finished successfully")
                else:
                    self.update_status(f"Program finished with errors ({return_code})")
                    
            except Exception as e:
                self.append_terminal(f"Runtime Error: {e}")
                self.update_status("Runtime Error")
            finally:
                self.process = None
                
        thread = threading.Thread(target=run_thread)
        thread.daemon = True
        thread.start()
        
    def compile_and_run(self):
        self.update_status("Compiling and Running...")
        
        def compile_and_run_thread():
            if self.compile_code():
                time.sleep(2)
                if hasattr(self, 'temp_executable') and os.path.exists(self.temp_executable):
                    time.sleep(1)
                    self.run_code()
                    
        thread = threading.Thread(target=compile_and_run_thread)
        thread.daemon = True
        thread.start()
        
    def stop_execution(self):
        if self.process:
            try:
                self.process.terminate()
                self.append_terminal("Program stopped by the user")
                self.update_status("Program stopped")
            except:
                pass
            finally:
                self.process = None
        else:
            self.update_status("No running program")
            
    def execute_terminal_command(self, event):
        command = self.terminal_input.get().strip()
        if command:
            self.append_terminal(f"$ {command}")
            self.terminal_input.delete(0, tk.END)
            
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write(command + '\n')
                    self.process.stdin.flush()
                except:
                    self.append_terminal("Error sending data to the program")
            else:
                self.execute_system_command(command)
                
    def execute_system_command(self, command):
        try:
            if command.lower() in ['clear', 'cls']:
                self.terminal_output.config(state='normal')
                self.terminal_output.delete(1.0, tk.END)
                self.terminal_output.config(state='disabled')
                return
                
            if command.lower() == 'help':
                help_text = """
Available commands:

- clear/cls: Clear the terminal
- dir: List files
- cd <directory>: Change directory
- Other system commands
                """
                self.append_terminal(help_text)
                return
                
            result = subprocess.run(command, shell=True, capture_output=True, 
                                  text=True, timeout=10)
            
            if result.stdout:
                self.append_terminal(result.stdout)
            if result.stderr:
                self.append_terminal(f" {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.append_terminal("Command timed out")
        except Exception as e:
            self.append_terminal(f"Runtime Error: {e}")
            
    def clean_build(self):
        try:
            files_removed = 0
            
            if hasattr(self, 'temp_source') and os.path.exists(self.temp_source):
                os.unlink(self.temp_source)
                files_removed += 1
                
            if hasattr(self, 'temp_executable') and os.path.exists(self.temp_executable):
                os.unlink(self.temp_executable)
                files_removed += 1
                
            self.clear_output()
            self.append_output(f"Cleared {files_removed} temporary files")
            self.update_status("Build cleared")
            
        except Exception as e:
            self.append_output(f"Error during cleaning: {e}")
            
    def show_about(self):
        about_text = """
C++ IDE

Features:

- Code editor
- C++ compilation and execution
- Interactive terminal
- Compiler configuration
- Support for multiple C++ standards
- Keyboard shortcuts

Shortcuts:

- Ctrl+N - New file
- Ctrl+O - Open file
- Ctrl+S - Save file
- F5 - Compile
- F6 - Compile and run
- F7 - Run

Help - Terminal
        """
        messagebox.showinfo("About", about_text)
        
    def on_closing(self):
        if self.process:
            self.process.terminate()
            
        try:
            if hasattr(self, 'temp_source') and os.path.exists(self.temp_source):
                os.unlink(self.temp_source)
            if hasattr(self, 'temp_executable') and os.path.exists(self.temp_executable):
                os.unlink(self.temp_executable)
        except:
            pass
            
        self.root.destroy()

def main():
    compilers = ['g++', 'clang++', 'gcc']
    available_compiler = None
    
    for compiler in compilers:
        try:
            subprocess.run([compiler, '--version'], capture_output=True, timeout=5)
            available_compiler = compiler
            break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
            
    if not available_compiler:
        print("Warning: C++ compiler not found!")
        print("Install one of the following: g++, clang++, gcc")
        print("\nThe application will run, but compilation will not work.\n")
        
    root = tk.Tk()
    app = CppCompilerIDE(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    print("Running C++ Compiler IDE...")
    print("\nIDE is ready for use!")
    
    root.mainloop()

if __name__ == "__main__":
    main()