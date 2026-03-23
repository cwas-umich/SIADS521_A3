import hvplot.pandas
import pandas as pd
import numpy as np
import panel as pn
import holoviews as hv

#filepaths for our data
file2025 = './items-2025-01-01-2026-01-01.csv'
file2026 = './items-2026-01-01-2027-01-01.csv'
filepath_weather = '4266263.csv'

weather_df = pd.read_csv(filepath_weather)
df_2025 = pd.read_csv(file2025)
df_2026 = pd.read_csv(file2026)

# joining the two sales data dfs
df_raw = pd.concat([df_2025, df_2026]).reset_index(drop=True)
df_raw['Gross Sales'] = df_raw['Gross Sales'].str.replace(r'[\$,]', '', regex=True).astype(float)
df_raw['Date'] = pd.to_datetime(df_raw['Date'])

df_clean = df_raw[['Date', 'Item', 'Gross Sales', 'Qty', 'Category']]

df_ytd_compare = df_clean.groupby('Date')['Gross Sales'].sum().reset_index()
df_ytd_compare['Year'] = df_ytd_compare['Date'].dt.year
df_ytd_compare['DayOfYear'] = df_ytd_compare['Date'].dt.dayofyear

max_day = df_ytd_compare.loc[df_ytd_compare['Year'] == 2026, 'DayOfYear'].max() - 1
# did -1 because the report was not run at the end of the day. so using the day before as the boundary. 
ytd_filtered = df_ytd_compare[df_ytd_compare['DayOfYear'] <= max_day].copy()
ytd_filtered['YTD'] = ytd_filtered.groupby('Year')['Gross Sales'].cumsum()

pn.extension()

ytd_line = ytd_filtered.pivot(
    index='DayOfYear', columns='Year', values='YTD'
).hvplot.line(
    title='YTD Gross Sales Comparison',
    xlabel='Day of Year', ylabel='Cumulative Revenue ($)',
    width=1050, height=350
)

#start the panel 

# cleaning up the data to work with our new column
ytd_filtered['DayOfWeek'] = ytd_filtered['Date'].dt.day_name() 
ytd_filtered['MonthNum'] = ytd_filtered['Date'].dt.month.astype(str)
ytd_filtered['Year'] = ytd_filtered['Year'].astype(str)
ytd_filtered['WeekOfYear'] = ytd_filtered['Date'].dt.isocalendar().week.astype(str)
ytd_filtered['DayOfMonth'] = ytd_filtered['Date'].dt.day.astype(str)


df_2025 = ytd_filtered[ytd_filtered['Year'] == '2025'] 
df_2026 = ytd_filtered[ytd_filtered['Year'] == '2026']

def make_heatmap(view):
    if view == 'Month x Day of Week':
        x, y = 'DayOfWeek', 'MonthNum'
    elif view == 'Month x Day of Month':
        x, y = 'DayOfMonth', 'MonthNum'
    elif view == 'Week x Day of Week':
        x, y = 'DayOfWeek', 'WeekOfYear'
    elif view == 'Year x Month':
        x, y = 'MonthNum', 'Year'

    left = df_2025.hvplot.heatmap(
        x=x, y=y, C='Gross Sales',
        reduce_function='sum', cmap='viridis',
        title='2025', width=525, height=400
    )
    right = df_2026.hvplot.heatmap(
        x=x, y=y, C='Gross Sales',
        reduce_function='sum', cmap='viridis',
        title='2026', width=525, height=400
    )
    return (left + right).cols(2)

heatmap_toggle = pn.widgets.RadioButtonGroup(
    name='View',
    options=['Month x Day of Week', 'Month x Day of Month', 'Week x Day of Week', 'Year x Month'],
    button_type='success'
)
# daily averages per year
avg_2025 = df_2025['Gross Sales'].mean()
avg_2026 = df_2026['Gross Sales'].mean()
diff = avg_2026 - avg_2025
pct_change = (diff / avg_2025) * 100

# print(f"2025 avg daily gross sales: ${avg_2025:,.2f}")
# print(f"2026 avg daily gross sales: ${avg_2026:,.2f}")
# print(f"Difference: ${diff:,.2f} ({pct_change:+.1f}%)")

# projected full year 2026 revenue
projected_2026 = avg_2026 * 365
# what 2025 would have been at its own pace
projected_2025_pace = avg_2025 * 365

# print(f"\nProjected 2026 full year (at current pace): ${projected_2026:,.2f}")
# print(f"2025 pace full year equivalent: ${projected_2025_pace:,.2f}")
# print(f"Projected additional revenue: ${projected_2026 - projected_2025_pace:,.2f}")

item_summary = df_clean.groupby('Item').agg(
    total_qty=('Qty', 'sum'),
    total_revenue=('Gross Sales', 'sum'),
    transaction_count=('Date', 'count')
).sort_values('total_revenue', ascending=False).reset_index()

item_summary['Category'] = df_clean['Category']
item_summary['revenue_pct'] = (item_summary['total_revenue'] / item_summary['total_revenue'].sum() * 100).round(2)
item_summary['cumulative_pct'] = item_summary['revenue_pct'].cumsum().round(2)

def abc_label(pct):
    if pct <= 80:
        return 'A'
    elif pct <= 95:
        return 'B'
    else:
        return 'C'

item_summary['ABC'] = item_summary['cumulative_pct'].apply(abc_label)


abc_counts = item_summary.groupby('ABC').agg(
    items=('Item', 'count'),
    revenue=('total_revenue', 'sum')
).reset_index()
abc_counts['revenue_k'] = (abc_counts['revenue'] / 1000).round(1)
items_bar = abc_counts.hvplot.bar(
    x='ABC', y='items', color='ABC',
    cmap={'A': '#d62728', 'B': '#ff7f0e', 'C': '#aec7e8'},
    title='Number of Items per ABC Tier',
    ylabel='Item Count', width=400, height=350
)

revenue_bar = abc_counts.hvplot.bar(
    x='ABC', y='revenue_k', color='ABC',
    cmap={'A': '#d62728', 'B': '#ff7f0e', 'C': '#aec7e8'},
    title='Revenue per ABC Tier (in $K)',
    ylabel='Revenue ($K)', width=400, height=350
)

def tier_detail(tier):
    tier_data = item_summary[item_summary['ABC'] == tier].sort_values('total_revenue', ascending=False)
    color = {'A': '#d62728', 'B': '#ff7f0e', 'C': '#aec7e8'}[tier]

    top_n = tier_data.head(20)
    bar = top_n.hvplot.barh(
        x='Item', y='total_revenue', color=color,
        title=f'Tier {tier} - Top Items by Revenue',
        ylabel='Revenue ($)', xlabel='Item',
        width=600, height=max(300, len(top_n) * 25)
    )

    summary = pn.pane.Markdown(f"""
**Tier {tier} Summary**
- Items: {len(tier_data)}
- Total Revenue: ${tier_data["total_revenue"].sum():,.2f}
- Avg Revenue per Item: ${tier_data["total_revenue"].mean():,.2f}
""")
    return pn.Column(summary, bar)

tier_toggle = pn.widgets.RadioButtonGroup(
    name='Tier',
    options=['A', 'B', 'C'],
    button_type='success'
)


core = ['Ice Cream', 'Ice', 'H2O \\ water', 'Bottles \\ Jugs', 'Lids for bottles']
months = ytd_filtered['Date'].dt.to_period('M').nunique()

cuttable = item_summary[
    (~item_summary['Category'].isin(core)) & 
    (item_summary['ABC'] != 'A')
].copy()

cuttable['avg_qty_month'] = cuttable['total_qty'] / months
cuttable['avg_revenue_month'] = cuttable['total_revenue'] / months

cuttable['cut_candidate'] = (
    (cuttable['avg_qty_month'] < 5) & 
    (cuttable['avg_revenue_month'] < 20)
)

scatter = cuttable.hvplot.scatter(
    x='avg_qty_month', y='avg_revenue_month',
    color='cut_candidate',
    cmap={True: 'red', False: 'green'},
    hover_cols=['Item', 'Category', 'ABC'],
    title='Cut Candidates (Red) vs Keepers (Green)',
    xlabel='Avg Qty Sold / Month', ylabel='Avg Revenue / Month ($)',
    width=700, height=450
)

hline = hv.HLine(20).opts(color='red', line_dash='dashed')
vline = hv.VLine(5).opts(color='red', line_dash='dashed')

cut_scatter = scatter * hline * vline

#cuttable[cuttable['cut_candidate'] == True][['Item', 'avg_qty_month', 'avg_revenue_month']].sort_values('avg_revenue_month')


cols = ['DATE', 'PRCP', 'TAVG', 'TMAX']
weather_df = weather_df[cols]
weather_df['DATE'] = pd.to_datetime(weather_df['DATE'])

dfw_clean = df_clean.merge(weather_df, left_on='Date', right_on='DATE', how='left').drop(columns='DATE')
dfw_daily = dfw_clean.groupby('Date').agg(
    Gross_Sales=('Gross Sales', 'sum'),
    Qty=('Qty', 'sum'),
    PRCP=('PRCP', 'first'),
    TAVG=('TAVG', 'first'),
    TMAX=('TMAX', 'first')
).reset_index()

#pn.extension()

temp_slider = pn.widgets.RangeSlider(
    name='TMAX Range (f)',
    start=int(dfw_daily['TMAX'].min()),
    end=int(dfw_daily['TMAX'].max()),
    value=(int(dfw_daily['TMAX'].min()), int(dfw_daily['TMAX'].max())),
    step=1
)
def filtered_scatter(temp_range):
    filtered = dfw_daily[
        (dfw_daily['TMAX'] >= temp_range[0]) & 
        (dfw_daily['TMAX'] <= temp_range[1])
    ]
    avg_sales = filtered['Gross_Sales'].mean()
    
    # rolling average by temperature
    temp_avg = filtered.groupby('TMAX')['Gross_Sales'].mean().reset_index()
    
    weather_scatter = filtered.hvplot.scatter(
        x='TMAX', y='Gross_Sales',
        xlabel='Max Temp (F)', ylabel='Gross Sales ($)',
        width=700, height=400, alpha=0.4,
        label='Daily Sales'
    )
    
    avg_line = temp_avg.hvplot.line(
        x='TMAX', y='Gross_Sales',
        color='orange', line_width=2,
        label='Avg Sales by Temp'
    )
    
    threshold = hv.HLine(avg_sales).opts(color='red', line_dash='dashed')
    
    plot = (weather_scatter * avg_line * threshold).opts(
        title=f'Avg Daily Sales: ${avg_sales:,.2f} | Days: {len(filtered)}',
        legend_position='top_left'
    )
    
    return plot

dashboard = pn.Column(
    pn.pane.Markdown('# POS Sales Analysis Dashboard'),

    pn.pane.Markdown('## 1. YTD Revenue Comparison'),
    ytd_line,

    pn.layout.Divider(),
    pn.pane.Markdown('## 2. Sales Heatmaps by Year'),
    heatmap_toggle,
    pn.bind(make_heatmap, heatmap_toggle),

    pn.layout.Divider(),
    pn.pane.Markdown('## 3. ABC Classification'),
    (items_bar + revenue_bar).cols(2),
    tier_toggle,
    pn.bind(tier_detail, tier_toggle),

    pn.layout.Divider(),
    pn.pane.Markdown('## 4. Cut Candidate Analysis'),
    cut_scatter,

    pn.layout.Divider(),
    pn.pane.Markdown('## 5. Weather Impact on Sales'),
    temp_slider,
    pn.bind(filtered_scatter, temp_slider),
)

dashboard.show()
