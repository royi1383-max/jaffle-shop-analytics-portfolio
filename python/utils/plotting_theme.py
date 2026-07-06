"""Shared visual theme for all charts in this project."""

COLORS = {
    "primary":   "#4C78A8",
    "secondary": "#F58518",
    "success":   "#54A24B",
    "danger":    "#E45756",
    "neutral":   "#72B7B2",
    "purple":    "#B279A2",
    "food":      "#F58518",
    "beverage":  "#4C78A8",
}

SEGMENT_COLORS = {
    "Champions":          "#2E86AB",
    "Loyal Customers":    "#54A24B",
    "Potential Loyalists":"#72B7B2",
    "At Risk":            "#F58518",
    "Cannot Lose Them":   "#E45756",
    "Recent Customers":   "#B279A2",
    "Lost":               "#9E9E9E",
}

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, Arial, sans-serif", size=13),
    paper_bgcolor="white",
    plot_bgcolor="#FAFAFA",
    margin=dict(l=40, r=20, t=50, b=40),
    colorway=list(COLORS.values()),
)


def apply_theme(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor="#EEEEEE", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE", zeroline=False)
    return fig
