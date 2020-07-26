from tkinter import *

import pandas as pd

status_values = ['Backlog', 'Tried', 'Regret', 'Completed', 'Playing']
length_values = ['Short', 'Long', 'Infinite']

# Import the main database
db = pd.read_pickle('data/main_db')


class Randomizer:
    def __init__(self):

        # Define root Window and title
        self.root = Tk()
        self.title = Label(self.root, text='Game Randomizer', font=(None, 24)).grid(row=0, column=1)

        # Define Status Listbox
        self.statusframe = Frame(master=self.root, padx=15, pady=15)
        self.statusframe.grid(column=0, row=1, sticky=W, rowspan=2)
        self.status = Listbox(master=self.statusframe, selectmode=MULTIPLE, font=(None, 16), width=10,
                              exportselection=0)
        self.status.pack()
        for item in status_values:
            self.status.insert(END, item)

        # Define Length Listbox
        self.lengthframe = Frame(master=self.root, padx=15, pady=15)
        self.lengthframe.grid(column=2, row=1, sticky=E, rowspan=2)
        self.length = Listbox(master=self.lengthframe, selectmode=MULTIPLE, font=(None, 16), width=10,
                              exportselection=0)
        self.length.pack()
        for item in length_values:
            self.length.insert(END, item)

        # Define Subscription Checkbox
        self.checkframe = Frame(master=self.root)
        self.checkframe.grid(column=1, row=1, sticky=N, pady=30)
        self.sub_or_not = IntVar()
        self.subs = Checkbutton(master=self.checkframe, text='Exclude Subscriptions', variable=self.sub_or_not,
                                onvalue=1, offvalue=0, font=(None, 10))
        self.subs.pack()

        # Define Generate Button
        self.generateframe = Frame(master=self.root)
        self.generateframe.grid(column=1, row=2)
        self.generatebutton = Button(master=self.generateframe, text='Generate', height=2, width=20, font=(None, 15),
                                     command=self.generate)
        self.generatebutton.pack()

        # Define Output Variable
        self.outputframe = Frame(master=self.root)
        self.outputframe.grid(column=1, row=3)
        self.outputvar = StringVar()
        self.output = Label(self.outputframe, text='PlaceHolder\nStatus - Backlog\nLength - Infinite',
                            font=(None, 18), textvariable=self.outputvar)
        self.output.pack()

    def generate(self):

        # If nothing is selected, then select all values
        status_list = list(status_values[item] for item in self.status.curselection())
        if not status_list:
            status_list = status_values

        length_list = list(length_values[item] for item in self.length.curselection())
        if not length_list:
            length_list = length_values

        # Filter according to values selected
        temp_view = db.copy()
        temp_view = temp_view[temp_view['Status'].isin(status_list)]
        temp_view = temp_view[temp_view['Length'].isin(length_list)]
        if self.sub_or_not.get():
            temp_view = temp_view[~temp_view['Platform'].str.match('Xbox Gamepass|Origin Premiere')]
        row = temp_view.sample()
        title, status, length = row['Title'].values[0], row['Status'].values[0], row['Length'].values[0]
        labelval = title + '\n' + 'Status - ' + status + '\n' + 'Length - ' + length
        self.outputvar.set(labelval)


randomize_gui = Randomizer()
randomize_gui.root.mainloop()
