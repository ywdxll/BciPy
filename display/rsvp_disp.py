# -*- coding: utf-8 -*-

from __future__ import division
from psychopy import visual
import numpy as np


class DisplayRSVP(object):
    """ RSVP Display Object for Sequence Presentation. Animates a sequence
        in RSVP. Mode should be determined outside.
        Attr:
            task(visual_Text_Stimuli): task bar
            text(list[visual_Text_Stimuli]): text bar, there can be
                different number of information texts in different paradigms
            sti(visual_Text_Stimuli): stimuli text
            bg(BarGraph): bar graph display unit in display
            trialClock(core_clock): timer for presentation """

    def __init__(self, window, clock, experiment_clock, color_task=['white'], font_task='Times',
                 pos_task=(-.8, .9), task_height=0.2, text_task='1/100',
                 color_text=['white'], text_text=['Information Text'],
                 font_text=['Times'], pos_text=[(.8, .9)], height_text=[0.2],
                 font_sti='Times', pos_sti=(-.8, .9), sti_height=0.2,
                 ele_list_sti=['a'] * 10, color_list_sti=['white'] * 10,
                 time_list_sti=[1] * 10,
                 tr_pos_bg=(.5, .5), bl_pos_bg=(-.5, -.5), size_domain_bg=7,
                 color_bg_txt='red', font_bg_txt='Times', color_bar_bg='green',
                 bg_step_num=20, is_txt_sti=1):
        """ Initializes RSVP window parameters and objects
            Args:
                window(visual_window): Window in computer
                color_task(list[string]): Color of the task string. Shares the
                    length of the text_task. If of length 1 the entire task
                    bar shares the same color.
                font_task(string): Font of task string
                pos_task(tuple): position of task string
                task_height(float): height for task string
                text_task(string): text of the task bar

                text_text(list[string]): text list for information texts
                color_text(list[string]): Color of the text string
                font_text(list[string]): Font of text string
                pos_text(list[tuple]): position of text string
                task_height(list[float]): height for text string

                sti_height(float): height of the stimuli object
                pos_sti(tuple): position of stimuli
                font_sti(string): font of the stimuli
                ele_list_sti(list[string]): list of elements to flash
                color_list_sti(list[string]): list of colors for stimuli
                time_list_sti(list[float]): timing for each letter flash

                tr_pos_bg(tuple): top right corner location of bar graph
                bl_pos_bg(tuple): bottom left corner location of bar graph
                size_domain_bg(int): number of elements in bar graph
                color_bg_txt(string): color of bar graph text
                font_bg_txt(string): font of bar graph text
                color_bar_bg(string): color of bar graph bars
                bg_step_num(int): number of animation iterations for bars
                """
        self.win = window

        self.ele_list_sti = ele_list_sti
        self.color_list_sti = color_list_sti
        self.time_list_sti = time_list_sti

        self.is_txt_sti = is_txt_sti

        self.trialClock = clock
        self.expClock = experiment_clock

        # Length of the stimuli (number of flashes)
        self.len_sti = len(ele_list_sti)

        # Check if task text is multicolored
        if len(color_task) == 1:
            self.task = visual.TextStim(win=window, color=color_task[0],
                                        height=task_height,
                                        text=text_task,
                                        font=font_task, pos=pos_task,
                                        wrapWidth=None, colorSpace='rgb',
                                        opacity=1, depth=-6.0)
        else:
            self.task = MultiColorText(win=window, list_color=color_task,
                                       height=task_height,
                                       text=text_task,
                                       font=font_task, pos=pos_task,
                                       wrapWidth=None, colorSpace='rgb',
                                       opacity=1, depth=-6.0)

        # Create multiple text objects based on input
        self.text = []
        for idx in range(len(text_text)):
            self.text.append(visual.TextStim(win=window, color=color_text[idx],
                                             height=height_text[idx],
                                             text=text_text[idx],
                                             font=font_text[idx],
                                             pos=pos_text[idx],
                                             wrapWidth=None, colorSpace='rgb',
                                             opacity=1, depth=-6.0))

        # Create Stimuli Object
        if self.is_txt_sti:
            self.sti = visual.TextStim(win=window, color='white',
                                       height=sti_height, text='+',
                                       font=font_sti, pos=pos_sti,
                                       wrapWidth=None, colorSpace='rgb',
                                       opacity=1, depth=-6.0)
        else:
            self.sti = visual.ImageStim(win=window, image=None, mask=None,
                                        units='', pos=pos_sti,
                                        size=(sti_height, sti_height), ori=0.0)

        # Create Bar Graph
        self.bg = BarGraph(win=window, tr_pos_bg=tr_pos_bg,
                           bl_pos_bg=bl_pos_bg,
                           size_domain=size_domain_bg,
                           color_txt=color_bg_txt, font_bg=font_bg_txt,
                           color_bar_bg=color_bar_bg, max_num_step=bg_step_num)

    def draw_static(self):
        """ Draws static elements in a stimulus. """
        self.task.draw()
        for idx in range(len(self.text)):
            self.text[idx].draw()

    def schedule_to(self, ele_list=[], time_list=[], color_list=[]):
        """ Schedules stimuli elements (works as a buffer)
            Args:
                ele_list(list[string]): list of elements of stimuli
                time_list(list[float]): list of timings of stimuli
                color_list(list[string]): colors of elements of stimuli """
        self.ele_list_sti = ele_list
        self.time_list_sti = time_list
        self.color_list_sti = color_list

    def update_task(self, text, color_list, pos):
        """ Updates Task Object
            Args:
                text(string): text for task
                color_list(list[string]): list of the colors for each char
                pos(tuple): position of task """
        if len(color_list) == 1:
            self.task.text = text
            self.task.color = color_list[0]
            self.task.pos = pos
        else:
            self.task.update(text=text, color_list=color_list, pos=pos)

    def do_sequence(self):
        """ Animates a sequence  """

        # init an array for timing information
        timing = []

        # Do the sequence
        for idx in range(len(self.ele_list_sti)):
            self.trialClock.start(self.time_list_sti[idx])
            if self.is_txt_sti:
                self.sti.text = self.ele_list_sti[idx]
                self.sti.color = self.color_list_sti[idx]
            else:
                self.sti.image = self.ele_list_sti[idx]

            self.draw_static()
            self.sti.draw()

            if self.is_txt_sti:
                timing.append((self.sti.text, self.expClock.getTime()))
            else:
                end = self.sti.image.rfind('.')
                start= self.sti.image.rfind('\\') + 1
                timing.append((self.sti.image[start:end], self.expClock.getTime()))

            self.win.flip()
            self.trialClock.complete()

        self.draw_static()
        self.win.flip()

        return timing

    def show_bar_graph(self):
        """ Animates Bar Graph """

        for idx in range(self.bg.max_num_step):
            self.draw_static()
            self.bg.animate(idx)
            self.win.flip()

    def update_task_state(self, text, color_list):
        """ Updates task state of Free Spelling Task by removing letters or
            appending to the right.
            Args:
                text(string): new text for task state
                color_list(list[string]): list of colors for each """
        tmp = visual.TextStim(self.win, font=self.task.font, text=text)
        x_pos_task = tmp.boundingBox[0] / self.win.size[0] - 1
        pos_task = (x_pos_task, 1 - self.task.height)

        self.update_task(text=text, color_list=color_list, pos=pos_task)



class MultiColorText(object):
    """ Implementation of multi color Text Stimuli. Psychopy does not
        support multiple color texts. Draws multiple TextStim elements on
        the screen with different colors.
            Attr:
                texts(list[TextStim]): characters that form the string """

    def __init__(self, win, list_color=['red'] * 5, height=0.2,
                 text='dummy_text', font='Times', pos=(0, 0), wrapWidth=None,
                 colorSpace='rgb', opacity=1, depth=-6.0):
        """ Initializes multi color text
            Args:
                win(visual_window): display window
                text(string): string to be displayed
                list_color(list[string]): list of colors of the string
                height(float): height of each character
                pos(tuple): center position of the multi color text

                wrapWidth, colorSpace, opacity, depth : to keep consistency
                     of the visual object definition (required in TextStim)
                """
        self.win = win
        self.pos = pos
        self.text = text
        self.font = font
        self.height = height
        self.list_color = list_color
        self.wrapWidth = wrapWidth
        self.colorSpace = colorSpace
        self.opacity = opacity
        self.depth = depth

        self.texts = []

        # Align characters using pixel wise operations
        width_total_in_pix = 0
        for idx in range(len(list_color)):
            self.texts.append(
                visual.TextStim(win=win, color=list_color[idx], height=height,
                                text=text[idx], font=font, pos=(0, 0),
                                wrapWidth=wrapWidth, colorSpace=colorSpace,
                                opacity=opacity, depth=depth))
            # Bounding box provides pixel information of each letter
            width_total_in_pix += self.texts[idx].boundingBox[0]

        # Window goes from [-1,1], therefore we need to multiply by 2
        x_pos_text = pos[0] - (width_total_in_pix / win.size[0])
        for idx in range(len(list_color)):
            len_txt = self.texts[idx].boundingBox[0] / win.size[0]
            self.texts[idx].pos = (x_pos_text + len_txt, pos[1])
            x_pos_text += len_txt * 2

    def draw(self):
        """ Draws multi color text on screen """
        for idx in range(len(self.texts)):
            self.texts[idx].draw()

    def update(self, text, color_list, pos):
        """ Updates (Re-creates) the multicolor text object. It is more
            compact to erase the previous one and recreate a new object.
            Args:
                text(string): string to be displayed
                color_list(list[string]): list of colors of the string
                pos(tuple): position of the multicolor text """
        # Align characters using pixel wise operations
        width_total_in_pix = 0
        self.texts = []
        for idx in range(len(color_list)):
            self.texts.append(
                visual.TextStim(win=self.win, color=color_list[idx],
                                height=self.height,
                                text=text[idx], font=self.font, pos=(0, 0),
                                wrapWidth=self.wrapWidth,
                                colorSpace=self.colorSpace,
                                opacity=self.opacity, depth=self.depth))
            # Bounding box provides pixel information of each letter
            width_total_in_pix += self.texts[idx].boundingBox[0]

        # Window goes from [-1,1], therefore we need to multiply by 2
        x_pos_text = pos[0] - (width_total_in_pix / self.win.size[0])
        for idx in range(len(color_list)):
            len_txt = self.texts[idx].boundingBox[0] / self.win.size[0]
            self.texts[idx].pos = (x_pos_text + len_txt, pos[1])
            x_pos_text += len_txt * 2


class BarGraph(object):
    """ Bar Graph object for RSVP Display
        Attr:
            texts(list[visual_Text_Stimuli]): items to show
            bars(list[visual_Rect_Stimuli]): corresponding density bars """

    def __init__(self, win, tr_pos_bg=(.5, .5), bl_pos_bg=(-.5, -.5),
                 size_domain=10, color_txt='white', font_bg='Times',
                 color_bar_bg='white', max_num_step=20):
        """ Initializes Bar Graph parameters
            Args:
                win(visual_window): display window
                tr_pos_bg(tuple) - bl_pos_bg(tuple): bar graph lies in a
                rectangular region in window tr(top right) and bl(bottom
                left) are tuples of (x,y) coordinates of corresponding edges
                size_domain(int): number of items to be shown
                color_txt(string): color of the letters
                font_bg(string): font of letters
                color_bar_bg(string): color of density bars
                max_num_step(int): maximum number of steps for animation """

        self.win = win
        self.bl_pos = bl_pos_bg
        self.tr_pos = tr_pos_bg
        self.size_domain = size_domain

        letters = ['a'] * size_domain

        self.height_text_bg = (tr_pos_bg[1] - bl_pos_bg[1]) / self.size_domain
        # TODO: insert aspect ratio parameter
        self.width_text_bg = 0.8 * abs(self.height_text_bg)

        self.texts, self.bars = [], []
        for idx in range(size_domain):
            shift = idx * self.height_text_bg
            pos_text = tuple([self.bl_pos[0] + self.width_text_bg / 2,
                              self.bl_pos[
                                  1] + self.height_text_bg / 2 + shift])
            pos_bar = tuple(
                [(self.tr_pos[0] + self.bl_pos[0] + self.width_text_bg) / 2,
                 self.bl_pos[1] + self.height_text_bg / 2 + shift])
            width_bar = (
                            pos_bar[0] - (
                                self.bl_pos[0] + self.width_text_bg)) * 2
            self.texts.append(
                visual.TextStim(win=win, color=color_txt,
                                height=self.height_text_bg, text=letters[idx],
                                font=font_bg, pos=pos_text, wrapWidth=None,
                                colorSpace='rgb', opacity=1, depth=-6.0))
            self.bars.append(
                visual.Rect(win=win, width=width_bar,
                            height=self.height_text_bg,
                            fillColor=color_bar_bg, fillColorSpace='rgb',
                            lineColor=None,
                            pos=pos_bar))

        self.weight_bars = [0] * self.size_domain
        self.scheduled_arg = self.weight_bars
        self.scheduled_weight = letters
        self.max_num_step = max_num_step

    def update(self, letters, weight):
        """ Updates bar graph parameters
            Args:
                letters(list[char]): characters to be displayed
                weight(list[float]): densities of characters to be displayed
        """
        for idx in range(self.size_domain):
            shift = idx * self.height_text_bg
            x_bar = (self.bl_pos[0] + self.width_text_bg) + (weight[idx] * (
                self.tr_pos[0] - (self.bl_pos[0] + self.width_text_bg))) / 2
            pos_bar = tuple([x_bar,
                             self.bl_pos[1] + self.height_text_bg / 2 + shift])
            width_bar = (
                            pos_bar[0] - (
                                self.bl_pos[0] + self.width_text_bg)) * 2
            self.texts[idx].text = letters[idx]
            self.bars[idx].pos = pos_bar
            self.bars[idx].width = width_bar

    def draw(self):

        for idx in range(self.size_domain):
            self.texts[idx].draw()
            self.bars[idx].draw()

    def schedule_to(self, letters, weight):
        """ Schedules bar graph
            Args:
                letters(list[char]): characters to be displayed
                weight(list[float]): densities of characters to be displayed
        """
        self.scheduled_arg = letters
        self.scheduled_weight = list(
            np.array(weight) / np.sum(np.array(weight)))

    def animate(self, step):
        """ Animates bar graph to the scheduled position
            Args:
                step(int): <max_num_step, >0, updates to given step number
        """

        weight_ani = []
        for idx in range(self.size_domain):
            weight_ani = list(np.asarray(self.weight_bars) + (
                np.asarray(self.scheduled_weight) - np.asarray(
                    self.weight_bars)) / self.max_num_step * step)
            self.update(self.scheduled_arg, weight_ani)
            self.draw()

        self.weight_bars = weight_ani

    def reset_weights(self):
        """ Resets the bar graph parameters """
        self.weight_bars = list(np.ones(self.size_domain) / self.size_domain)
