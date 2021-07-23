"""Originally Adapted from sphinxcontrib.details.directive
"""
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.docutils import SphinxDirective

from sphinx_design.shared import (
    SEMANTIC_COLORS,
    create_component,
    is_component,
    make_choice,
)

from .icons import get_octicon, list_octicons


def setup_dropdown(app: Sphinx) -> None:
    app.add_node(dropdown_main, html=(visit_dropdown_main, depart_dropdown_main))
    app.add_node(dropdown_title, html=(visit_dropdown_title, depart_dropdown_title))
    app.add_directive("dropdown", DropdownDirective)
    app.add_post_transform(DropdownHtmlTransform)


class dropdown_main(nodes.Element, nodes.General):
    pass


class dropdown_title(nodes.TextElement, nodes.General):
    pass


def visit_dropdown_main(self, node):
    if node.get("opened"):
        self.body.append(self.starttag(node, "details", open="open"))
    else:
        self.body.append(self.starttag(node, "details"))


def depart_dropdown_main(self, node):
    self.body.append("</details>")


def visit_dropdown_title(self, node):
    self.body.append(self.starttag(node, "summary"))


def depart_dropdown_title(self, node):
    self.body.append("</summary>")


class DropdownDirective(SphinxDirective):
    """A directive to generate a collapsible container.

    Note: This directive generates a single container,
    for the title (optional) and content::

        <container design_component="dropdown" has_title=True>
            <rubric>
                ...title nodes
        ...content nodes

    This allows for a default rendering in non-HTML outputs.

    The ``DropdownHtmlTransform`` then transforms this container
    into the HTML specific structure.
    """

    optional_arguments = 1  # title of dropdown
    final_argument_whitespace = True
    has_content = True
    option_spec = {
        "open": directives.flag,  # make open by default
        "color": make_choice(SEMANTIC_COLORS),
        "icon": make_choice(list_octicons()),
        "animate": make_choice(("fade-in", "fade-in-slide-down")),
        "name": directives.unchanged,
        "class-container": directives.class_option,
        "class-title": directives.class_option,
        "class-body": directives.class_option,
    }

    def run(self):
        """Run the directive"""
        # default classes
        classes = {
            "container_classes": self.options.get("class-container", ["sd-mb-3"]),
            "title_classes": self.options.get("class-title", []),
            "body_classes": self.options.get("class-body", []),
        }

        # add color classes
        title_color = self.options.get("color")
        if title_color:
            classes["title_classes"].extend(
                [f"sd-bg-{title_color}", f"sd-bg-text-{title_color}"]
            )

        # add animation classes
        if (
            "animate" in self.options
            and ("sd-" + self.options["animate"]) not in classes["container_classes"]
        ):
            classes["container_classes"].append("sd-" + self.options["animate"])

        container = create_component(
            "dropdown",
            opened="open" in self.options,
            type="dropdown",
            has_title=len(self.arguments) > 0,
            icon=self.options.get("icon"),
            **classes,
        )
        self.set_source_info(container)
        if self.arguments:
            textnodes, messages = self.state.inline_text(self.arguments[0], self.lineno)
            container += nodes.rubric(self.arguments[0], "", *textnodes)
            container += messages
        self.state.nested_parse(self.content, self.content_offset, container)
        self.add_name(container)
        return [container]


# Note the custom octicon here has thicker dots than:
# get_octicon("kebab-horizontal", classes="no-title", size=24)
KEBAB = """\
<svg viewBox="0 0 36 24" width="36" height="16" xmlns="http://www.w3.org/2000/svg"
    class="octicon no-title" aria-hidden="true">
  <g xmlns="http://www.w3.org/2000/svg" class="jp-icon3">
    <circle cx="0" cy="12" r="6"></circle>
    <circle cx="18" cy="12" r="6"></circle>
    <circle cx="36" cy="12" r="6"></circle>
  </g>
</svg>"""


class DropdownHtmlTransform(SphinxPostTransform):
    """Transform dropdown containers into the HTML specific AST structures::

    <details class="sd-sphinx-override sd-dropdown sd-card">
        <summary class="sd-summary-title sd-card-header">
            ...title nodes
        <div class="sd-summary-content sd-card-body">
            ...content nodes

    """

    default_priority = 200
    formats = ("html",)

    def run(self):
        """Run the transform"""
        for node in self.document.traverse(lambda node: is_component(node, "dropdown")):

            # TODO option to not have card css (but requires more formatting)
            use_card = True

            open_marker = create_component(
                "dropdown-open-marker",
                classes=["sd-summary-up"],
                children=[
                    nodes.raw(
                        "",
                        nodes.Text(get_octicon("chevron-up", size=24)),
                        format="html",
                    )
                ],
            )
            closed_marker = create_component(
                "dropdown-closed-marker",
                classes=["sd-summary-down"],
                children=[
                    nodes.raw(
                        "",
                        nodes.Text(get_octicon("chevron-down", size=24)),
                        format="html",
                    )
                ],
            )

            newnode = dropdown_main(
                opened=node["opened"],
                classes=["sd-sphinx-override", "sd-dropdown"]
                + (["sd-card"] if use_card else ["sd-d-flex"])
                + node["container_classes"],
            )

            if node["has_title"]:
                title_children = node[0].children
                body_children = node[1:]
            else:
                title_children = [
                    nodes.raw(
                        "...",
                        nodes.Text(KEBAB),
                        format="html",
                    )
                ]
                body_children = node.children
            if node["icon"]:
                title_children.insert(
                    0,
                    nodes.raw(
                        "",
                        nodes.Text(get_octicon(node["icon"], size=16)),
                        classes=["sd-summary-icon"],
                        format="html",
                    ),
                )

            newnode += dropdown_title(
                "",
                "",
                *title_children,
                closed_marker,
                open_marker,
                classes=["sd-summary-title"]
                + (["sd-card-header"] if use_card else [])
                + node["title_classes"],
            )
            body_node = create_component(
                "dropdown-body",
                classes=["sd-summary-content"]
                + (["sd-card-body"] if use_card else [])
                + node["body_classes"],
                children=body_children,
            )
            if use_card:
                for para in body_node.traverse(nodes.paragraph):
                    para["classes"] = ([] if "classes" in para else para["classes"]) + [
                        "sd-card-text"
                    ]
            newnode += body_node
            # newnode += open_marker
            node.replace_self(newnode)