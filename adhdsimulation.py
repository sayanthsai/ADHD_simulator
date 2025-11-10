import tkinter as tk
from tkinter import messagebox
import pygame
import threading
import random
import time
from abc import ABC, abstractmethod
import os # For listing meme files
from PIL import Image, ImageTk # For loading and resizing images

# ------------------------
# Configuration & Globals
# ------------------------
# NOTE: You must have 'na.mp3', '1.mp3', '2.mp3', '3.mp3' files in the same directory.
# You also need a 'memes' folder with meme images (e.g., meme1.png) inside it.
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
BG_COLOR = "#f0f0f0"
TASK_FONT = ("Helvetica", 16, "bold")
UI_FONT = ("Helvetica", 12)
DISTRACTION_COLORS = ["#ff9999", "#99ff99", "#9999ff", "#ffff99", "#ffcc00", "#cc00ff"] # More vibrant colors
DISTRACTION_SHAPES = ["oval", "rectangle", "triangle"] # Added triangle

MEME_FOLDER = "memes"
MEME_SIZE = 300
MEME_DURATION_MS = 3000 # 3 seconds

# ------------------------
# Initialize Pygame Mixer
# ------------------------
try:
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except pygame.error:
    print("Warning: Pygame mixer failed to initialize. Audio distractions will be disabled.")
    AUDIO_AVAILABLE = False

# Load meme image paths
MEME_IMAGES = []
if os.path.exists(MEME_FOLDER):
    for filename in os.listdir(MEME_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            MEME_IMAGES.append(os.path.join(MEME_FOLDER, filename))
    if not MEME_IMAGES:
        print(f"Warning: '{MEME_FOLDER}' folder exists but contains no image files.")
else:
    print(f"Warning: '{MEME_FOLDER}' folder not found. Meme image distractions will be disabled.")


# ------------------------
# Abstract Base Task Class
# ------------------------
class BaseTask(ABC):
    """Abstract base class for all focus tasks."""
    def __init__(self, simulator, text):
        self.simulator = simulator
        self.root = simulator.root
        self.text = text
        self.widgets = [] # To keep track of task-specific widgets

    def setup(self):
        """Prepares the UI for the task."""
        self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: {self.text}")
        self._setup_task_ui()

    @abstractmethod
    def _setup_task_ui(self):
        """Internal method to be implemented by subclasses."""
        pass

    def cleanup(self):
        """Destroys all task-specific widgets."""
        for widget in self.widgets:
            widget.destroy()
        self.widgets.clear()
        # Ensure default buttons/entry are reset
        self.simulator.task_button.config(state="disabled", text="")
        self.simulator.entry_field.pack_forget()

    def complete(self):
        """Called when the task is successfully finished."""
        self.cleanup()
        self.simulator.complete_current_task()

# ------------------------
# Specific Task Implementations (Same as before, no changes needed here)
# ------------------------

class ClickTask(BaseTask):
    """Task requiring a specific number of button clicks."""
    def __init__(self, simulator, text, target):
        super().__init__(simulator, text)
        self.target = target
        self.click_count = 0

    def _setup_task_ui(self):
        self.simulator.task_button.config(
            state="normal",
            text=f"Click Me ({self.click_count}/{self.target})",
            command=self._handle_click
        )

    def _handle_click(self):
        self.click_count += 1
        self.simulator.task_button.config(text=f"Click Me ({self.click_count}/{self.target})")
        if self.click_count >= self.target:
            self.complete()

class TypeTask(BaseTask):
    """Task requiring typing a specific word."""
    def __init__(self, simulator, text, target):
        super().__init__(simulator, text)
        self.target = target.lower()

    def _setup_task_ui(self):
        self.simulator.entry_field.delete(0, tk.END)
        self.simulator.entry_field.pack(pady=10)
        self.simulator.entry_field.focus_set()
        self.simulator.entry_field.unbind("<Return>") # Clear previous bindings
        self.simulator.entry_field.bind("<Return>", self._check_typing)

    def _check_typing(self, event=None):
        if self.simulator.entry_field.get().strip().lower() == self.target:
            self.complete()
        else:
            self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: {self.text} (Incorrect, try again)")
            self.simulator.entry_field.delete(0, tk.END)

class ComboTask(BaseTask):
    """Task requiring both typing a word and clicking a button."""
    def __init__(self, simulator, text, target_word, target_clicks=1):
        super().__init__(simulator, text)
        self.target_word = target_word.lower()
        self.target_clicks = target_clicks
        self.typed_correctly = False
        self.clicked_correctly = 0

    def _setup_task_ui(self):
        self.simulator.entry_field.delete(0, tk.END)
        self.simulator.entry_field.pack(pady=10)
        self.simulator.entry_field.unbind("<Return>")
        self.simulator.entry_field.bind("<Return>", self._check_combo_type)

        self.simulator.task_button.config(
            state="normal",
            text="Click Target",
            command=self._check_combo_click
        )

    def _check_combo_type(self, event=None):
        if self.simulator.entry_field.get().strip().lower() == self.target_word:
            self.typed_correctly = True
            self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: {self.text} (Type done, now click!)")
        else:
            self.typed_correctly = False
            self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: {self.text} (Type failed, re-type)")

        if self.typed_correctly and self.clicked_correctly >= self.target_clicks:
            self.complete()

    def _check_combo_click(self):
        self.clicked_correctly += 1
        self.simulator.task_button.config(text=f"Click Target ({self.clicked_correctly}/{self.target_clicks})")
        if self.typed_correctly and self.clicked_correctly >= self.target_clicks:
            self.complete()
        elif self.clicked_correctly >= self.target_clicks and not self.typed_correctly:
            pass

class ArrangeTask(BaseTask):
    """Task requiring clicking items in a specific order (ascending)."""
    def __init__(self, simulator, text, sequence):
        super().__init__(simulator, text)
        self.sequence = sequence
        self.current_index = 0
        self.task_buttons = []

    def _setup_task_ui(self):
        numbers = list(self.sequence)
        random.shuffle(numbers)

        for i, num in enumerate(numbers):
            btn = tk.Button(
                self.root,
                text=str(num),
                font=("Arial", 14),
                relief=tk.RAISED,
                bg="#cccccc",
                command=lambda n=num: self._check_number(n)
            )
            btn.place(x=300 + i * 100, y=300, width=80, height=40)
            self.widgets.append(btn)

    def _check_number(self, n):
        if n == self.sequence[self.current_index]:
            self.current_index += 1
            if self.current_index == len(self.sequence):
                self.complete()
            else:
                self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: Click {self.sequence[self.current_index]}")
        else:
            self.current_index = 0
            self.simulator.task_label.config(text=f"Task {self.simulator.current_task_index + 1}: {self.text} (Wrong order, try again from {self.sequence[0]})")


# ------------------------
# Main Application Class
# ------------------------
class ADHDFocusSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("ADHD Focus Simulator (Enhanced Distractions)")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        self.tasks_data = [
            ClickTask(self, "Click the button 5 times", target=5),
            TypeTask(self, "Type the word 'focus'", target="focus"),
            ClickTask(self, "Click the button 3 times", target=3),
            TypeTask(self, "Type the word 'attention'", target="attention"),
            ArrangeTask(self, "Arrange numbers in ascending order (click 1, 2, 3)", sequence=[1, 2, 3]),
            ComboTask(self, "Type 'go' and then click 'Target'", target_word="go"),
            TypeTask(self, "Form the word from letters 'c o d e'", target="code")
        ]
        self.current_task_index = 0
        self.current_task = None

        # Distraction Management
        self.distraction_canvas_objects = [] # Stores canvas IDs of shapes
        self.meme_image_references = {} # Stores PhotoImage objects to prevent garbage collection
        self.meme_canvas_objects = [] # Stores canvas IDs of meme images

        self.running_distractions = False
        self.audio_timer = None
        self.visual_shape_timer = None
        self.visual_meme_timer = None

        self._setup_ui()

    def _setup_ui(self):
        """Sets up the main Tkinter widgets."""
        self.canvas = tk.Canvas(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg=BG_COLOR, highlightthickness=0)
        self.canvas.place(x=0, y=0)

        self.task_label = tk.Label(self.root, text="Welcome to the ADHD Focus Simulator", font=TASK_FONT, bg=BG_COLOR, fg="#333333")
        self.task_label.pack(pady=40)

        self.task_button = tk.Button(self.root, text="", state="disabled", font=UI_FONT, bg="#dddddd", relief=tk.FLAT)
        self.task_button.pack(pady=10, ipadx=10, ipady=5)

        self.entry_field = tk.Entry(self.root, font=UI_FONT, bd=2, relief=tk.SUNKEN, justify='center')
        self.entry_field.pack_forget()

        self.start_button = tk.Button(self.root, text="Start Simulation", font=TASK_FONT, command=self.start_simulation, bg="#4CAF50", fg="white", relief=tk.RAISED)
        self.start_button.pack(pady=30, ipadx=20, ipady=10)

    # --- Simulation Control ---

    def start_simulation(self):
        """Starts narration, hides start button, and initiates the first task."""
        if AUDIO_AVAILABLE:
            self.task_label.config(text="Narration started... listen carefully.")
            try:
                pygame.mixer.music.load("na.mp3")
                pygame.mixer.music.set_volume(0.6)
                pygame.mixer.music.play(-1) # Loop the main audio track
            except pygame.error as e:
                print(f"Error loading/playing na.mp3: {e}")

        self.start_button.destroy()
        self.start_task(self.current_task_index)
        self.root.after(15000, self.start_distractions) # distractions start after 15s

    def start_task(self, index):
        """Initializes and sets up the specified task."""
        if self.current_task:
            self.current_task.cleanup()

        self.current_task_index = index
        self.current_task = self.tasks_data[index]
        self.current_task.setup()

    def complete_current_task(self):
        """Moves to the next task or ends the simulation."""
        self.current_task_index += 1
        if self.current_task_index < len(self.tasks_data):
            self.start_task(self.current_task_index)
        else:
            self.end_simulation()

    def end_simulation(self):
        """Stops all distractions and shows the completion message."""
        if AUDIO_AVAILABLE:
            pygame.mixer.music.stop()
        
        self.stop_distractions()
        self.task_label.config(text="All tasks completed! ✅", fg="#008000")
        
        messagebox.showinfo(
            "Simulation Complete",
            "Congratulations! You’ve completed all the tasks.\n\nReflect on how it felt to maintain focus with continuous distractions."
        )

    # --- Distraction Management ---

    def start_distractions(self):
        """Initiates both visual and audio distractions."""
        if self.running_distractions:
            return

        self.running_distractions = True
        print("Distractions Activated!")
        
        self._spawn_visual_shape_distraction() # Regular shapes
        if MEME_IMAGES:
            self._spawn_meme_distraction()      # Meme images

        if AUDIO_AVAILABLE:
            self._play_audio_distraction()

    def stop_distractions(self):
        """Stops all running distractions and cleans up canvas objects."""
        self.running_distractions = False
        
        if self.visual_shape_timer:
            self.root.after_cancel(self.visual_shape_timer)
        if self.visual_meme_timer:
            self.root.after_cancel(self.visual_meme_timer)
        if self.audio_timer:
            self.root.after_cancel(self.audio_timer)

        for obj in self.distraction_canvas_objects + self.meme_canvas_objects:
            self.canvas.delete(obj)
        self.distraction_canvas_objects.clear()
        self.meme_canvas_objects.clear()
        self.meme_image_references.clear() # Clear image references

    # --- Visual Shape Distractions (Enhanced) ---
    def _spawn_visual_shape_distraction(self):
        """Creates a new animated shape and schedules its movement and eventual disappearance."""
        if not self.running_distractions:
            return

        shape_type = random.choice(DISTRACTION_SHAPES)
        x = random.randint(50, WINDOW_WIDTH - 100)
        y = random.randint(100, WINDOW_HEIGHT - 100)
        initial_size = random.randint(30, 70)
        color = random.choice(DISTRACTION_COLORS)
        
        obj = None
        if shape_type == "oval":
            obj = self.canvas.create_oval(x, y, x + initial_size, y + initial_size, fill=color, outline="")
        elif shape_type == "rectangle":
            obj = self.canvas.create_rectangle(x, y, x + initial_size, y + initial_size, fill=color, outline="")
        elif shape_type == "triangle":
            # Create a simple equilateral triangle
            h = initial_size * (3**0.5) / 2 # height of equilateral triangle
            obj = self.canvas.create_polygon(x, y + h, x + initial_size/2, y, x + initial_size, y + h, fill=color, outline="")


        self.distraction_canvas_objects.append(obj)
        
        # Initial animation parameters
        direction_x = random.choice([-1, 1])
        direction_y = random.choice([-1, 1])
        move_speed = random.randint(1, 3)
        rotate_angle = random.randint(-5, 5) if shape_type != "oval" else 0 # Ovals don't visibly rotate
        size_change = random.choice([-1, 0, 1]) # -1:shrink, 0:no change, 1:grow

        self._animate_shape_distraction(obj, direction_x, direction_y, move_speed, rotate_angle, size_change)

        # Schedule the next shape spawning
        self.visual_shape_timer = self.root.after(random.randint(2000, 5000), self._spawn_visual_shape_distraction)

        # Schedule the object's cleanup after a duration
        self.root.after(random.randint(8000, 12000), lambda: self._remove_distraction_obj(obj, self.distraction_canvas_objects))


    def _animate_shape_distraction(self, obj, dx, dy, speed, rotation_step, size_step):
        """Applies dynamic movement, size, and rotation to a canvas shape."""
        if not self.running_distractions or obj not in self.distraction_canvas_objects:
            return

        try:
            # Movement
            self.canvas.move(obj, dx * speed, dy * speed)

            # Get current bounding box for bounds checking and sizing
            x1, y1, x2, y2 = self.canvas.coords(obj)

            # Bounce off edges
            if x1 < 0 or x2 > WINDOW_WIDTH:
                dx *= -1
            if y1 < 0 or y2 > WINDOW_HEIGHT:
                dy *= -1
            
            # Size change (only apply if within reasonable bounds)
            current_width = x2 - x1
            current_height = y2 - y1
            
            if size_step != 0:
                new_width = current_width + size_step
                new_height = current_height + size_step
                if 20 < new_width < 100 and 20 < new_height < 100: # Keep within reasonable size
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    self.canvas.coords(obj, center_x - new_width/2, center_y - new_height/2,
                                            center_x + new_width/2, center_y + new_height/2)

            # Rotation (Tkinter canvas shapes don't have built-in rotation like images)
            # This would require more complex polygon recalculation or converting to image.
            # For now, we'll omit visible rotation on basic shapes or use a workaround if feasible.
            # Given the request is "slow meme images" and "distraction animations", we'll keep it simple for shapes.

            self.root.after(50, lambda: self._animate_shape_distraction(obj, dx, dy, speed, rotation_step, size_step))
        except tk.TclError:
            # Object might have been deleted, ignore
            pass

    # --- Meme Image Distractions ---
    def _spawn_meme_distraction(self):
        """Spawns a meme image on the canvas for a short duration."""
        if not self.running_distractions or not MEME_IMAGES:
            return

        meme_path = random.choice(MEME_IMAGES)
        try:
            # Load and resize image using PIL (Pillow)
            pil_image = Image.open(meme_path)
            pil_image = pil_image.resize((MEME_SIZE, MEME_SIZE), Image.LANCZOS)
            tk_image = ImageTk.PhotoImage(pil_image)

            x = random.randint(0, WINDOW_WIDTH - MEME_SIZE)
            y = random.randint(0, WINDOW_HEIGHT - MEME_SIZE)

            # Create image on canvas
            canvas_image_id = self.canvas.create_image(x, y, anchor=tk.NW, image=tk_image)

            # Store reference to prevent garbage collection
            self.meme_image_references[canvas_image_id] = tk_image
            self.meme_canvas_objects.append(canvas_image_id)

            # Schedule disappearance
            self.root.after(MEME_DURATION_MS,
                            lambda: self._remove_distraction_obj(canvas_image_id, self.meme_canvas_objects, self.meme_image_references))

        except Exception as e:
            print(f"Error loading or displaying meme '{meme_path}': {e}")

        # Schedule next meme spawn
        self.visual_meme_timer = self.root.after(random.randint(5000, 10000), self._spawn_meme_distraction) # Memes less frequent than shapes

    def _remove_distraction_obj(self, obj_id, obj_list, image_refs=None):
        """Removes a single distraction object from the canvas and tracking lists."""
        try:
            self.canvas.delete(obj_id)
            if obj_id in obj_list:
                obj_list.remove(obj_id)
            if image_refs and obj_id in image_refs:
                del image_refs[obj_id] # Crucial for PhotoImage objects
        except:
            pass # Already deleted or not found

    # --- Audio Distractions (Same as before) ---
    def _play_audio_distraction(self):
        """Plays a random short audio clip and schedules the next one."""
        if not self.running_distractions or not AUDIO_AVAILABLE:
            return

        distraction_sounds = ["1.mp3", "2.mp3", "3.mp3"]
        sound_file = random.choice(distraction_sounds)
        
        try:
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(0.05)
            threading.Thread(target=lambda: sound.play()).start()
        except pygame.error as e:
            print(f"Error playing sound file {sound_file}: {e}")
            
        self.audio_timer = self.root.after(random.randint(5000, 9000), self._play_audio_distraction)


# ------------------------
# Application Start
# ------------------------
if __name__ == "__main__":
    # Create the 'memes' folder if it doesn't exist (for user convenience)
    if not os.path.exists(MEME_FOLDER):
        os.makedirs(MEME_FOLDER)
        print(f"Created '{MEME_FOLDER}' folder. Please place meme images inside it.")
    
    root = tk.Tk()
    app = ADHDFocusSimulator(root)
    root.mainloop()
