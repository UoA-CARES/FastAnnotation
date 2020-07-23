import time
from threading import Lock

import kivy.utils
from kivy.app import App
from kivy.clock import mainthread
from kivy.properties import BooleanProperty
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

import client.utils as utils
from client.controller.instance_annotator_controller import InstanceAnnotatorController
from client.model.instance_annotator_model import InstanceAnnotatorModel
from client.screens.common import *
from client.screens.paint_window import PaintWindow
from client.utils import background

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'instance_annotator_screen.kv'))


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    tab_panel = ObjectProperty(None)

    _update_lock = Lock()
    _update_flag = False

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.model = InstanceAnnotatorModel()
        self.controller = InstanceAnnotatorController(self.model)

    def get_current_image_canvas(self):
        if not isinstance(self.tab_panel.current_tab, ImageCanvasTab):
            return None
        return self.tab_panel.current_tab.image_canvas

    def queue_update(self):
        with self._update_lock:
            if not self._update_flag:
                self._update_flag = True
                self._update()

    @mainthread
    def _update(self):
        # TODO: Implement a diff system which only updates changed sections of
        # the model

        t0 = time.time()

        current_iid = self.model.tool.get_current_image_id()
        current_label_name = self.model.tool.get_current_label_name()
        current_layer = self.model.tool.get_current_layer_name()

        t1 = time.time()
        # Update ToolSelect
        self.left_control.tool_select.alpha.value = self.model.tool.get_alpha()
        self.left_control.tool_select.pen_size.value = self.model.tool.get_pen_size()

        t2 = time.time()
        # Update Class Picker
        label_names = self.model.labels.keys()
        labels = []
        for name in label_names:
            with self.model.labels.get(name) as label:
                labels.append(label)

        self.left_control.class_picker.load_labels(labels)
        self.left_control.class_picker.select(current_label_name)  # MEM 10.7 -> 11.9 (+1.2GB)

        t3 = time.time()
        # Update Layer View

        tt0 = time.time()
        tt1 = time.time()

        with self.model.images.get(current_iid) as image:
            tt1 = time.time()
            if image is not None and image.annotations is not None:

                self.left_control.layer_view.load_layer_items(image.annotations.values())
        tt2 = time.time()

        self.left_control.layer_view.select(
            self.model.tool.get_current_layer_name())

        tt3 = time.time()
        print("\t[LV] | %f, %f, %f" % (tt1-tt0, tt2-tt1, tt3-tt2))


        t4 = time.time()
        # Update ImageCanvas

        tt0 = time.time()
        if current_iid > 0 and not self.tab_panel.has_tab(current_iid):
            self.tab_panel.add_tab(current_iid)  # MEM 11.9 -> 18.2 (+5.1GB)
            tab = self.tab_panel.get_tab(current_iid)
            self.tab_panel.switch_to(tab, do_scroll=True)

        tt1 = time.time()
        image_canvas = self.get_current_image_canvas()
        with self.model.labels.get(current_label_name) as current_label:
            with self.model.images.get(current_iid) as image:
                if image_canvas is not None:
                    image_canvas.load_pen_size(self.model.tool.get_pen_size())
                    image_canvas.load_global_alpha(self.model.tool.get_alpha())
                    if image_canvas.load_annotations(image.annotations):
                        self.models.images.add(current_iid, image)
                    image_canvas.load_current_layer(current_layer)
                    image_canvas.load_current_label(current_label)

        tt2 = time.time()
        print("\t[IC] | %f, %f" % (tt1- tt0, tt2-tt1))
        t5 = time.time()
        # Update ImageQueue
        self.right_control.load_image_queue()

        with self.model.images.get(current_iid) as image:
            if image is not None:
                self.tab_panel.current_tab.unsaved = image.unsaved

            if image is not None and image.unsaved:
                self.right_control.image_queue_control.btn_save.disabled = False
            else:
                self.right_control.image_queue_control.btn_save.disabled = True
        t6 = time.time()
        # Reset update flag
        with self._update_lock:
            self._update_flag = False
        print("[CLIENT: %.4f] | Init: %f\tToolSelect: %f\tClassPick: %f\tLayerView: %f\tImageC: %f\tImageQ: %f" %
              (time.time() - t0, t1 - t0, t2 - t1, t3 - t2, t4 - t3, t5 - t4, t6 - t5))

    def on_enter(self, *args):
        self.fetch_image_metas()
        self.fetch_class_labels()

    @background
    def load_next(self):
        image_ids = self.model.images.keys()
        current_id = self.model.tool.get_current_image_id()
        idx = 0
        if current_id > 0:
            idx = image_ids.index(current_id)
            idx += 1

        while True:
            with self.model.images.get(image_ids[idx]) as image:
                if not image.is_locked:
                    break
                else:
                    idx += 1
        next_id = image_ids[idx]
        self.controller.open_image(next_id)
        self.queue_update()

    @background
    def load_image(self, id):
        self.controller.open_image(id)
        self.queue_update()

    @mainthread
    def save_image(self):
        image_canvas = self.get_current_image_canvas()
        if image_canvas is None:
            return
        image_canvas.prepare_to_save()
        self._save_image()

    @background
    def _save_image(self):
        image_canvas = self.get_current_image_canvas()
        if image_canvas is None:
            return
        self.controller.save_image(image_canvas)
        self.queue_update()

    @background
    def add_layer(self):
        self.controller.add_blank_layer(self.model.tool.get_current_image_id())
        self.queue_update()

    @background
    def fetch_image_metas(self):
        filter_details = {
            "order_by": {
                "key": "name",
                "ascending": True
            }
        }
        self.controller.fetch_image_metas(
            self.app.current_project_id, filter_details)
        self.queue_update()

    @background
    def fetch_class_labels(self):
        self.controller.fetch_class_labels(self.app.current_project_id)
        if self.model.tool.get_current_label_name() is "":
            self.controller.update_tool_state(
                current_label=self.model.labels.keys()[0])
        self.queue_update()


class LeftControlColumn(BoxLayout):
    tool_select = ObjectProperty(None)
    class_picker = ObjectProperty(None)
    layer_view = ObjectProperty(None)


class ToolSelect(GridLayout):
    pen_size = ObjectProperty(None)
    alpha = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def set_alpha(self, alpha):
        print("Alpha: %s" % str(alpha))
        self.app.root.current_screen.controller.update_tool_state(alpha=alpha)
        self.app.root.current_screen.queue_update()

    def set_pencil_size(self, size):
        print("Pen Size: %s" % str(size))
        self.app.root.current_screen.controller.update_tool_state(
            pen_size=size)
        self.app.root.current_screen.queue_update()


class ClassPicker(GridLayout):
    current_label = ObjectProperty(None, allownone=True)
    grid = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.label_dict = {}

    def on_current_label(self, instance, value):
        class_name = ""
        if value is not None:
            class_name = value.class_name

        print("Label: %s" % str(class_name))
        self.app.root.current_screen.controller.update_tool_state(
            current_label=class_name)

        if class_name is not "":
            self.app.root.current_screen.controller.update_annotation(
                label_name=class_name)
        self.app.root.current_screen.queue_update()

    def clear(self):
        self.grid.clear_widgets()
        self.label_dict.clear()

    def select(self, name):
        label = self.label_dict.get(name, None)
        if label is None:
            return
        self._change_label(label)

    def load_labels(self, labels):
        deleted_labels = [self.label_dict[x] for x in self.label_dict.keys() if x not in [l.name for l in labels]]
        for l in deleted_labels:
            self.grid.remove_widget(l)
            self.label_dict.pop(l.name, None)

        for l in labels:
            if l.name not in self.label_dict:
                self.add_label(l.name, l.color)
            self.label_dict[l.name].class_color = l.color

    def add_label(self, name, color):
        item = self._make_label(name, color)
        self.grid.add_widget(item)
        self.label_dict[name] = item

    def _make_label(self, name, color):
        item = ClassPickerItem()
        item.class_name = name
        item.class_color = color
        item.enable_cb = item.enable
        item.disable_cb = item.disable
        item.bind(on_release=lambda *args: self._change_label(item))
        return item

    def _change_label(self, instance):
        if self.current_label:
            self.current_label.disable_cb()
        self.current_label = instance
        self.current_label.enable_cb()
        self.app.root.current_screen.queue_update()


class ClassPickerItem(Button):
    class_color = ObjectProperty((0, 0, 0, 1))
    class_name = StringProperty("")
    class_id = NumericProperty(-1)

    enable_cb = ObjectProperty(None)
    disable_cb = ObjectProperty(None)

    def enable(self):
        self.state = 'down'

    def disable(self):
        self.state = 'normal'


class LayerView(GridLayout):
    layer_item_layout = ObjectProperty(None)

    current_selection = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.layers = {}

    def on_current_selection(self, instance, value):
        layer_name = ""
        if value is None:
            print("Setting LayerView Layer to None")
        else:
            layer_name = value.layer_name
        print("Layer: %s" % str(value))
        self.app.root.current_screen.controller.update_tool_state(
            current_layer=layer_name)

    def clear(self):
        self.layer_item_layout.clear_widgets()
        self.layers.clear()

    def select(self, layer_name):
        item = self.layers.get(layer_name, None)
        if item is None:
            return
        self._change_layer(item)

    def load_layer_items(self, annotations):
        deleted_names = [x for x in self.layers if x not in [a.annotation_name for a in annotations]]
        for name in deleted_names:
            layer = self.layers.pop(name, None)
            if layer:
                self.layer_item_layout.remove_widget(layer)

        for a in annotations:
            if a.annotation_name not in self.layers:
                self.add_layer_item(a)
            self.layers[a.annotation_name].mask_enabled = a.mask_enabled
            self.layers[a.annotation_name].bbox_enabled = a.bbox_enabled

    def add_layer_item(self, annotation):
        item = LayerViewItem(annotation.annotation_name)
        item.layer_select_cb = lambda: self._change_layer(item)
        item.layer_delete_cb = lambda: self._delete_layer(item)
        item.mask_enabled = annotation.mask_enabled
        item.bbox_enabled = annotation.bbox_enabled
        self.layer_item_layout.add_widget(item)
        self.layers[annotation.annotation_name] = item

    def _change_layer(self, instance):
        if self.current_selection:
            self.current_selection.deselect()
        self.current_selection = instance
        self.current_selection.select()
        self.app.root.current_screen.queue_update()

    def _delete_layer(self, instance):
        if instance is self.current_selection:
            self.current_selection = None
        self.layer_item_layout.remove_widget(instance)
        iid = self.app.root.current_screen.model.tool.get_current_image_id()
        self.app.root.current_screen.controller.delete_layer(
            iid, instance.layer_name)
        self.app.root.current_screen.queue_update()


class LayerViewItem(RelativeLayout):
    layer_name = StringProperty('')
    mask_enabled = BooleanProperty(True)
    bbox_enabled = BooleanProperty(True)

    layer_select_cb = ObjectProperty(None)
    layer_delete_cb = ObjectProperty(None)

    btn_base = ObjectProperty(None)
    btn_mask = ObjectProperty(None)
    btn_bbox = ObjectProperty(None)

    button_down_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_HIGHLIGHT_1))
    button_up_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_DARK_3))

    def __init__(self, name, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.layer_name = name

    def on_mask_enabled(self, instance, value):
        self.btn_mask.background_color = self.button_down_color if value else self.button_up_color
        self.btn_mask.state = 'down' if value else 'normal'
        self.app.root.current_screen.controller.update_annotation(
            layer_name=self.layer_name, mask_enabled=value)
        self.app.root.current_screen.queue_update()

    def on_bbox_enabled(self, instance, value):
        self.btn_bbox.background_color = self.button_down_color if value else self.button_up_color
        self.btn_bbox.state = 'down' if value else 'normal'
        self.app.root.current_screen.controller.update_annotation(
            layer_name=self.layer_name, bbox_enabled=value)
        self.app.root.current_screen.queue_update()

    def select(self):
        self.btn_base.background_color = self.button_down_color
        self.btn_base.state = 'down'

    def deselect(self):
        self.btn_base.background_color = self.button_up_color
        self.btn_base.state = 'normal'


class Painter(RelativeLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.paint_window = None
        self.draw_tool = None

    def bind_image(self, image):
        self.clear_widgets()
        self.paint_window = PaintWindow(image)
        self.draw_tool = DrawTool(self.paint_window)
        self.add_widget(self.paint_window)
        self.add_widget(self.draw_tool)
        self.size = self.paint_window.size


class DrawTool(MouseDrawnTool):
    def __init__(self, paint_window, pen_size=10, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.paint_window = paint_window

        self.size_hint = (None, None)
        self.pen_size = pen_size
        self.keyboard.create_shortcut(("lctrl", "z"), self.paint_window.undo)
        self.keyboard.create_shortcut(("lctrl", "y"), self.paint_window.redo)
        self.keyboard.create_shortcut("spacebar", self.app.root.current_screen.add_layer)
        self.keyboard.activate()

        self.consecutive_clicks = 0

    def on_touch_down_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        if self.keyboard.is_key_down("lctrl"):
            selected = self.paint_window.detect_collision(touch.pos)
            if len(selected) > 0:
                layer_name = selected[self.consecutive_clicks % len(selected)]
                screen = self.app.root.current_screen
                screen.controller.update_tool_state(
                    current_layer=layer_name)
                screen.queue_update()
                self.consecutive_clicks += 1
        else:
            self.consecutive_clicks = 0
            if self.keyboard.is_key_down("shift"):
                self.paint_window.fill(pos)
            else:
                self.paint_window.draw_line(pos, self.pen_size)
        self.paint_window.queue_refresh()

    def on_touch_move_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, self.pen_size)
        self.paint_window.queue_refresh()

    def on_touch_up_hook(self, touch):
        self.paint_window.queue_checkpoint()
        self.paint_window.queue_refresh()


class ImageCanvasTabPanel(TabbedPanel):
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        super().__init__(**kwargs)

    def get_tab(self, iid):
        for tab in self.tab_list:
            if not isinstance(tab, ImageCanvasTab):
                continue
            if tab.image_canvas.image_id == iid:
                return tab
        return None

    def has_tab(self, iid):
        return self.get_tab(iid) is not None

    def add_tab(self, iid):
        with self.app.root.current_screen.model.images.get(iid) as image_model:  # MEM 11.9 -> 13.1 (+1.2GB)
            # Add Tab + Load everything
            tab = ImageCanvasTab(image_model.name)
            tab.image_canvas.painter.bind_image(image_model.image)
            tab.image_canvas.load_image(image_model)
            tab.image_canvas.load_annotations(image_model.annotations)  # 13.1 -> 18.2 (+5.1GB)
            self.add_widget(tab)

    def switch_to(self, header, do_scroll=False):
        if not isinstance(header, ImageCanvasTab):
            return
        if isinstance(self.current_tab, ImageCanvasTab):
            # self.current_tab.image_canvas.draw_tool.unbind_keyboard()
            pass

        # header.image_canvas.draw_tool.bind_keyboard()

        screen = self.app.root.current_screen
        screen.controller.update_tool_state(
            current_iid=header.image_canvas.image_id)
        screen.queue_update()
        return super(ImageCanvasTabPanel, self).switch_to(header, do_scroll)


class ImageCanvasTab(TabbedPanelItem):
    image_canvas = ObjectProperty(None)
    tab_name = StringProperty("")
    unsaved = BooleanProperty(False)

    def __init__(self, name, **kwargs):
        self.tab_name = name
        super().__init__(**kwargs)

    def get_iid(self):
        return self.image_canvas.image_id


class ImageCanvas(BoxLayout):
    painter = ObjectProperty(None)
    scatter = ObjectProperty(None)
    image_id = NumericProperty(-1)
    unsaved = BooleanProperty(False)

    max_scale = NumericProperty(10.0)
    min_scale = NumericProperty(0.5)
    step_scale = NumericProperty(0.1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def prepare_to_save(self):
        # Note: This method must be run on the main thread
        # for layer in self.layer_stack.get_all_layers():
        #     layer.prepare_matrix()
        # TODO
        pass

    def load_save_status(self, unsaved):
        self.unsaved = unsaved

    def load_pen_size(self, size):
        if self.painter.draw_tool is None:
            return
        self.painter.draw_tool.pen_size = size

    def load_global_alpha(self, alpha):
        self.painter.paint_window.image.opacity = alpha

    def load_current_label(self, label):
        if self.painter.paint_window is None or label is None:
            return
        self.painter.paint_window.set_color(label.get_rgb())
        self.painter.paint_window.queue_refresh()

    def load_current_layer(self, layer_name):
        if self.painter.paint_window is None or not layer_name:
            return

        if self.painter.paint_window.get_selected_layer() is layer_name:
            return

        self.painter.paint_window.select_layer(layer_name)
        self.painter.paint_window.queue_refresh(True)

    def load_image(self, image_state):
        if image_state is None:
            return
        # print("Loading Image")
        self.image_id = image_state.id
        # texture = utils.mat2texture(image_state.image)
        # self.image.texture = texture
        # self.image.size = image_state.shape[1::-1]
        # TODO is this needed? yes
        pass

    def load_annotations(self, annotations):
        print("Loading Annotations")
        names = []
        colors = []
        boxes = []
        box_vis = []
        masks = []
        mask_vis = []
        controller = self.app.root.current_screen.controller
        update_required = False
        for a in annotations.values():
            with self.app.root.current_screen.model.labels.get(a.class_name) as label:
                if label is not None:
                    colors.append(label.get_rgb())
                else:
                    colors.append([255, 255, 255])
                names.append(a.annotation_name)
                masks.append(a.mat)
                mask_vis.append(a.mask_enabled)
                if not utils.is_valid_bounds(a.bbox):
                    new_box = utils.fit_box(a.mat)
                    if not np.all(np.equal(new_box, a.bbox)):
                        a.bbox = new_box
                        update_required = True
                boxes.append(a.bbox)
                box_vis.append(a.bbox_enabled)
        if update_required:
            controller.load_annotations(annotations=annotations)
        self.painter.paint_window.load_layers(names, colors, masks, boxes, mask_vis, box_vis)

        #
        # if annotations is None:
        #     return
        #
        # if overwrite:
        #     self.layer_stack.clear()
        #
        # active_layers = [x.layer_name for x in self.layer_stack.get_all_layers()]
        # active_annotations = [x.annotation_name for x in annotations.values()]
        #
        # for layer_name in active_layers:
        #     if layer_name not in active_annotations:
        #         self.layer_stack.remove_layer(self.layer_stack.get_layer(layer_name))
        #
        # for annotation in annotations.values():
        #     layer = self.layer_stack.get_layer(annotation.annotation_name)
        #     if overwrite or layer is None:
        #         layer = DrawableLayer(
        #             layer_name=annotation.annotation_name,
        #             size=annotation.mat.shape[1::-1],
        #             texture=utils.mat2texture(annotation.mat),
        #             bbox=annotation.bbox)
        #         self.layer_stack.add_layer(layer)
        #     with self.app.root.current_screen.model.labels.get(annotation.class_name) as label:
        #         layer.update_label(label)
        #     layer.set_mask_visible(annotation.mask_enabled)
        #     layer.set_bbox_visible(annotation.bbox_enabled)
        # TODO
        pass

    def on_touch_down(self, touch):
        if self.painter.draw_tool.keyboard.is_key_down("lctrl") and touch.is_mouse_scrolling:
            if touch.button == 'scrolldown':
                self.zoom(1.0 + self.step_scale)
            elif touch.button == 'scrollup':
                self.zoom(1.0 - self.step_scale)

        # A Hack to ensure scatter doesnt have any dead zones
        self.scatter.size = self.scroll_view.size
        return super(ImageCanvas, self).on_touch_down(touch)

    def zoom(self, scale):
        print("pos: %s size: %s" % (str(self.scatter.pos),
                                    str(self.scatter.size)))
        self.scatter.scale = np.clip(self.scatter.scale * scale,
                                     self.min_scale,
                                     self.max_scale)
        self.scatter.pos = self.pos
        self.painter.pos = self.pos

        print("PosList: \n\tScatter: %s\n\tScrollView: %s\n\tPainter: %s\n\tPaintW: %s\n\tDrawTool: %s\n\t" %
              (str(self.scatter.pos), str(self.scroll_view.pos), str(self.painter.pos), str(self.painter.paint_window.pos), str(self.painter.draw_tool.pos)))
        print("SizeList: \n\tScatter: %s\n\tScrollView: %s\n\tPainter: %s\n\tPaintW: %s\n\tDrawTool: %s\n\t" %
              (str(self.scatter.size), str(self.scroll_view.size), str(self.painter.size), str(self.painter.paint_window.size),
               str(self.painter.draw_tool.size)))


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)
    image_queue_control = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def load_image_queue(self):
        image_ids = self.app.root.current_screen.model.images.keys()
        images = []
        for iid in image_ids:
            with self.app.root.current_screen.model.images.get(iid) as image:
                images.append(image)
        self.image_queue.load_items(images)


class ImageQueueControl(GridLayout):
    btn_save = ObjectProperty(None)


class ImageQueue(GridLayout):
    queue = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.queue_item_dict = {}

    def clear(self):
        self.queue.clear_widgets()
        self.queue_item_dict.clear()

    def load_items(self, images):
        deleted_items = [self.queue_item_dict[x] for x in self.queue_item_dict.keys() if x not in [img.id for img in images]]

        for item in deleted_items:
            self.queue_item_dict.pop(item, None)
            self.queue.remove_widget(item)

        for img in images:
            if img.id not in self.queue_item_dict:
                self.add_item(img.name, img.id, img.is_locked, img.is_open)

    def add_item(self, name, image_id, locked=False, opened=False):
        item = ImageQueueItem()
        item.image_name = name
        item.image_id = image_id
        item.set_status(lock=locked, opened=opened)
        self.queue.add_widget(item)
        self.queue_item_dict[image_id] = item


class ImageQueueItem(BoxLayout):
    image_name = StringProperty("")
    image_id = NumericProperty(0)
    button_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_DARK_3))
    image_open = BooleanProperty(False)
    image_locked = BooleanProperty(False)

    def set_status(self, opened=False, lock=False):
        self.image_open = opened
        self.image_locked = lock
        if opened:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_HIGHLIGHT_1)
        else:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_DARK_3)
