import Live
from typing import Tuple, Any, List, Optional
from .handler import AbletonOSCHandler

CATEGORIES = ("instruments", "drums", "sounds", "audio_effects", "midi_effects")


class BrowserHandler(AbletonOSCHandler):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "browser"

    def _root(self, category: str):
        if category not in CATEGORIES:
            raise ValueError("Unknown browser category: %s" % category)
        return getattr(Live.Application.get_application().browser, category)

    def _walk(self, category: str, path: Tuple[str, ...]):
        item = self._root(category)
        for segment in path:
            match = next((c for c in item.children if c.name == segment), None)
            if match is None:
                raise LookupError(
                    "No browser item named %r under %s/%s"
                    % (segment, category, "/".join(path))
                )
            item = match
        return item

    def init_api(self):
        def browser_list(params: Tuple[Any]):
            category = str(params[0])
            path = tuple(str(p) for p in params[1:])
            try:
                item = self._walk(category, path)
            except (ValueError, LookupError) as e:
                self.logger.warning(str(e))
                return (category, *path, 0)
            flat: List[Any] = []
            for child in item.children:
                # Live reports is_folder=False on top-level devices (e.g.
                # Operator) even though they have preset children. Peek at
                # len(child.children) so callers can navigate reliably.
                try:
                    has_children = len(child.children) > 0
                except Exception:
                    has_children = False
                flat.extend(
                    (
                        child.name,
                        int(bool(child.is_folder)),
                        int(bool(child.is_loadable)),
                        int(has_children),
                    )
                )
            return (category, *path, *flat)

        def browser_load(params: Tuple[Any]):
            track_index = int(params[0])
            category = str(params[1])
            path = tuple(str(p) for p in params[2:])
            try:
                item = self._walk(category, path)
            except (ValueError, LookupError) as e:
                self.logger.warning(str(e))
                return (track_index, 0, str(e))
            if not item.is_loadable:
                msg = "Browser item is not loadable: %s" % item.name
                self.logger.warning(msg)
                return (track_index, 0, msg)
            try:
                self.song.view.selected_track = self.song.tracks[track_index]
            except Exception as e:
                msg = "Couldn't select track %d: %s" % (track_index, e)
                self.logger.warning(msg)
                return (track_index, 0, msg)
            try:
                Live.Application.get_application().browser.load_item(item)
            except Exception as e:
                msg = "load_item failed: %s" % e
                self.logger.warning(msg)
                return (track_index, 0, msg)
            return (track_index, 1, item.name)

        self.osc_server.add_handler("/live/browser/list", browser_list)
        self.osc_server.add_handler("/live/browser/load", browser_load)
