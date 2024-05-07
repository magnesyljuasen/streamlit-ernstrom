import streamlit as st 
import pandas as pd
import streamlit.components.v1 as components
import numpy as np
import plotly.graph_objects as go
from elprice import CalculateCosts

def apply_co2_scaling(row, co2_array, scaling):
        return row * co2_array[row.name] / scaling

START_INDEX_SUMMER = 2183
END_INDEX_SUMMER = 6832

def hour_to_month(hourly_array, aggregation='sum'):
    result_array = []
    temp_value = 0 if aggregation in ['sum', 'max'] else []
    count = 0 if aggregation == 'average' else None
    for index, value in enumerate(hourly_array):
        if np.isnan(value):
            value = 0
        if aggregation == 'sum':
            temp_value += value
        elif aggregation == 'average':
            temp_value.append(value)
            count += 1
        elif aggregation == 'max' and value > temp_value:
            temp_value = value
        if index in [744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016, 8759]:
            if aggregation == 'average':
                if count != 0:
                    result_array.append(sum(temp_value) / count)
                else:
                    result_array.append(0)
                temp_value = []
                count = 0
            else:
                result_array.append(temp_value)
                temp_value = 0 if aggregation in ['sum', 'max'] else []
    return result_array

def get_winter_summer_parameters(array, mode = 'måned'):
    summer_max, winter_max = 0, 0
    if mode == 'måned':
        winter_sum = sum(array[i] for i in [0, 1, 2, 11, 10, 9])
        summer_sum = sum(array[i] for i in range(3, 9))
    else:
        summer_sum = sum(array[i] for i in range(1415, 6910))
        winter_sum = sum(array[i] for i in range(0, 1415)) + sum(array[i] for i in range(6910, 8760))
        winter_max = max(max(array[i] for i in range(0, 1415)), max(array[i] for i in range(6910, 8760)))
        summer_max = max(array[i] for i in range(1415, 6910))
        winter_max = int(winter_max)
        summer_max = int(summer_max)
    return int(round((winter_sum),0)), int(round((summer_sum),0)), winter_max, summer_max


def conditional_sum(array, mode = 'above'):
    new_array = []
    if mode == 'above':
        for index, value in enumerate(array):
            if value > 0:
                new_array.append(value)
            else:
                new_array.append(0)
    else:
        for index, value in enumerate(array):
            if value < 0:
                new_array.append(value)
            else:
                new_array.append(0)
    return int(round(sum(new_array),0))

st.cache_resource(show_spinner=False)
def read_df(sheet_name="Sheet1"):
    df = pd.read_excel("src/GeoTermosEksempel.xlsx", sheet_name=sheet_name)
    return df

def show_simple_plot(df, name, color='#1d3c34', ymin=0, ymax=1000, mode='hourly', type='positive', unit='kWh', hide_label = 'visible', reference_value = None):
    if type == 'positive':
        height = 200
    else:
        height = 150
    array = df[name].to_numpy()
    if mode == 'hourly':
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df.index, y=array, name='Values'))
        fig.update_traces(marker_color=color)
        fig.update_layout(
            yaxis=dict(tickformat=',d'),
            yaxis_range=[ymin, ymax],
            margin=dict(l=10, r=10, t=0, b=0),
            yaxis_ticksuffix=f" {unit[0:2]}",
            height=height,
            xaxis = dict(
                tickmode = 'array', 
                tickvals = [0, 24 * (31), 24 * (31 + 28), 24 * (31 + 28 + 31), 24 * (31 + 28 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30 + 31)], 
                ticktext = ["1.jan", "", "1.mar", "", "1.mai", "", "1.jul", "", "1.sep", "", "1.nov", "", "1.jan"],
                title=None,
                ))
        st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False, 'staticPlot': True})
    else:
        array = hour_to_month(array)
        fig = go.Figure()
        months = ['jan', 'feb', 'mar', 'apr', 'mai', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'des']
        fig.add_trace(go.Bar(x=months, y=array, name='Values'))
        fig.update_traces(marker_color=color)
        fig.update_layout(
            yaxis=dict(tickformat=',d'),
            yaxis_range=[ymin, ymax],
            margin=dict(l=10, r=10, t=0, b=0),
            yaxis_ticksuffix=f" {unit}",
            separators="* .*",
            height=height,)
        st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False, 'staticPlot': True})
    above_sum = conditional_sum(array=array, mode='above')
    below_sum = -conditional_sum(array=array, mode='below')
    if unit == 'kWh':
        label = 'Kjøpt strøm fra strømnettet'
    elif unit == 'Ingen':
        label = ''
    else:
        label = 'Utslipp med strøm (kg CO₂-ekv)'
    if reference_value == None:
        delta = None
    else:
        percentage_decrease = int(round(((reference_value - above_sum) / reference_value) * 100))
        delta = f'{percentage_decrease} % reduksjon'
    if type == 'positive':
        st.metric(label=label, value=f"{above_sum:,} {unit}".replace(",", " "), label_visibility=hide_label, delta=delta)
        winter_sum, summer_sum, winter_max, summer_max = get_winter_summer_parameters(array = array, mode = mode)
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Om vinteren")
            st.metric(label="Vinter", value=f"{winter_sum:,} {unit}".replace(",", " "), label_visibility="collapsed")
            if winter_max > 0 and unit != 'kg CO₂':
                st.metric(label="Vintereffekt", value=f"{winter_max:,} {unit[0:2]}".replace(",", " "), label_visibility="collapsed")
        with c2:
            st.caption("Om sommeren")
            st.metric(label="Sommer", value=f"{summer_sum:,} {unit}".replace(",", " "), label_visibility="collapsed")
            if summer_max > 0 and unit != 'kg CO₂':
                st.metric(label="Sommer", value=f"{summer_max:,} {unit[0:2]}".replace(",", " "), label_visibility="collapsed")       
    else:
        st.metric(label="Overskudd solstrømproduksjon", value=f"{below_sum:,} {unit}".replace(",", " "), label_visibility="collapsed")
    #st.metric(label="Balanse", value=f"{above_sum - below_sum:,} kWh".replace(",", " "))
    return above_sum

def show_costs_plot(calculate_costs_object, df, ymin=None, ymax=None, mode='hourly', type='positive', nettleie_mode=True, reference_value = None):
    if type == 'positive':
        height = 200
    else:
        height = 150
    calculate_costs_object.spotpris()
    calculate_costs_object.ekstra_nettleie_storre_naring()
    calculate_costs_object.hele_nettleie()
    calculate_costs_object.totaler()

    if calculate_costs_object.type_kunde != "Større næringskunde":
        fastledd_time = np.zeros(8760)
        fond_avgift_time = np.zeros(8760)
    else:
        fastledd_time = calculate_costs_object.fastledd_time
        fond_avgift_time = calculate_costs_object.fond_avgift_time

    nettleie = calculate_costs_object.energiledd_time + calculate_costs_object.kapledd_time + calculate_costs_object.offentlig_time + fastledd_time + fond_avgift_time
    if nettleie_mode == True:
        df = pd.DataFrame({
            'Nettleie': nettleie, 
            'Spotpris' : calculate_costs_object.spot_time
            })
    else:
        df = pd.DataFrame({
            'Spotpris' : calculate_costs_object.spot_time
            })
    if mode == 'hourly':
        fig = go.Figure()
        for col in df.columns[:-1]:
            fig.add_trace(go.Bar(x=df.index, y=df[col], name=col))
        fig.add_trace(go.Bar(x=df.index, y=df['Spotpris'], name='Spotpris'))
        fig.update_layout(
            yaxis=dict(tickformat=',d'),
            yaxis_ticksuffix=" kr",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='stack',
            #xaxis_title='Timer i ett år',
            separators="* .*",
            yaxis_range=[ymin, ymax],
            margin=dict(l=10, r=10, t=0, b=0),
            xaxis = dict(
                tickmode = 'array', 
                tickvals = [0, 24 * (31), 24 * (31 + 28), 24 * (31 + 28 + 31), 24 * (31 + 28 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30), 24 * (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30 + 31)], 
                ticktext = ["1.jan", "", "1.mar", "", "1.mai", "", "1.jul", "", "1.sep", "", "1.nov", "", "1.jan"],
                title=None,
                #showgrid=True
                ),
            height=height)
        st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False, 'staticPlot': True})
    else:
        months = ['jan', 'feb', 'mar', 'apr', 'mai', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'des']
        fig = go.Figure()
        for col in df.columns[:-1]:
            fig.add_trace(go.Bar(x=months, y=hour_to_month(df[col]), name=col))
        fig.add_trace(go.Bar(x=months, y=hour_to_month(df['Spotpris']), name='Spotpris'))
        fig.update_layout(
            yaxis=dict(tickformat=',d'),
            yaxis_ticksuffix=" kr",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='stack',
            separators="* .*",
            yaxis_range=[ymin, ymax],
            margin=dict(l=10, r=10, t=0, b=0),
            height=height)
        st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False, 'staticPlot': True})
    if nettleie_mode == True:
        total_array = df['Nettleie'] + df['Spotpris']
    else:
        total_array = df['Spotpris']
    above_sum = conditional_sum(array=total_array, mode='above')
    below_sum = -conditional_sum(array=total_array, mode='below')
    if reference_value == None:
        delta = None
    else:
        percentage_decrease = int(round(((reference_value - above_sum) / reference_value) * 100))
        delta = f'{percentage_decrease} % reduksjon'
    if type == 'positive':
        st.metric(label="Kjøpt energi", value=f"{above_sum:,} kr".replace(",", " "), delta=delta)
        return int(above_sum)
    else:
        st.metric(label="Salg av solstrøm", value=f"{below_sum:,} kr".replace(",", " "))
        return int(below_sum)
    


st.set_page_config(
    page_title="GeoTermos",
    layout="wide",
    initial_sidebar_state='expanded'
)

with open("styles/with_columns.css") as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

st.title("GeoTermos - regneeksempel")
st.success("Endre forutsetningene for beregningene i menyen til venstre", icon="ℹ️")

df = read_df()
df_positive = df.copy()
df_positive[df_positive < 0] = 0
df2 = read_df(sheet_name="Sheet2")
df3 = read_df(sheet_name="Sheet3")
#######################################
#######################################
calculate_costs_object = CalculateCosts(energy_demand = df['Elkjel'])
with st.sidebar:
    st.image(image = "src/av-logo.png", use_column_width=True, caption="Løsningen er laget av Asplan Viak for Ernströmgruppen")
with st.sidebar:
    mode = 'måned'
#    if st.toggle("Månedsplot", value = True):
#        mode='måned'
#    else:
#        mode='hourly'
    calculate_costs_object.streamlit_input()
calculate_costs_object.bestem_prissatser()
calculate_costs_object.dager_i_hver_mnd()
calculate_costs_object.energiledd()
calculate_costs_object.kapasitetsledd()
calculate_costs_object.offentlige_avgifter()

#######################################
#######################################
ymax_hourly = df3['Totalt'].max() * 1.1
ymax_monthly = np.max(hour_to_month(df3['Totalt'].to_numpy())) * 1.1
ymin_hourly = 0
ymin_monthly = 0

with st.expander("Energi- og effektbehov til bygget", expanded=False):
    st.write('''*Figurene viser energi- og effektbehovet til bygget. Elspesifikt behov er behovet 
            relatert til utstyr som drives av elektrisitet som elektriske apparater, 
            belysning, vifter og pumper. Romoppvarming og tappevannsbehov definerer 
            byggets behov for varme.* ''')
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        name = 'Elektrisk'
        color = '#367061'
        st.write(f"**Elspesifikt behov**")
        if mode == 'hourly':
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
        else:
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
    with c2:
        st.write(f"**Romoppvarmingsbehov**")
        name = 'Romoppvarming'
        color = '#367061'
        if mode == 'hourly':
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
        else:
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
    with c3:
        st.write(f"**Tappevannsbehov**")
        name = 'Tappevann'
        color = '#367061'
        if mode == 'hourly':
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
        else:
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
    with c4:
        st.write(f"**Totalt**")
        name = 'Totalt'
        color = '#367061'
        if mode == 'hourly':
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
        else:
            show_simple_plot(df3, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
    
    st.info(''' 💡 Det elspesifike behovet og tappevannsbehovet er nokså jevnt hele året - det er ingen store sesongvariasjoner. 
            Romoppvarmingsbehovet varierer med utetemperaturen og er mye høyere om vinteren enn sommeren.''')

#######################################
#######################################
ymax_hourly = df['Elkjel'].max() * 1.1
ymax_monthly = np.max(hour_to_month(df['Elkjel'].to_numpy())) * 1.1
ymin_hourly = np.min(df2['Energibrønner']) * 1.1
ymin_monthly = np.min(hour_to_month(df2['Energibrønner'].to_numpy())) * 1.1

with st.expander("Energiløsninger", expanded = False):
    st.write('''*Figurene viser energiflyten med 
             4 ulike energiløsninger til bygget. Dette er 
             altså mengden strøm må kjøpes fra strømnettet per år.* ''')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        name = 'Elkjel'
        color = '#1d3c34'
        st.caption("Alt 1)")
        st.write(f"**Elkjel og solceller**")
        st.markdown("---")
        st.write("*Kjøpt strøm fra strømnettet*")
        if mode == 'hourly':
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_hourly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        else:
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_monthly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        st.markdown("---")
    with c2:
        ###
        name = 'Fjernvarme og sol - strøm'
        color = '#485738'
        st.caption("Alt 2)")
        st.write(f"**Fjernvarme og solceller**")
        st.markdown("---")
        st.write("*Kjøpt strøm fra strømnettet*")
        if mode == 'hourly':
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_hourly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        else:
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_monthly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        st.markdown("---")
        ###
        name = 'Fjernvarme og sol - fjernvarme'
        color = '#485738'
        st.write("*Kjøpt fjernvarme*")
        if mode == 'hourly':
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
        else:
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
        st.markdown("---")
        with st.popover('Forenkling', use_container_width=True):
            st.write('''Det er gjort en forenkling om at utslippsfaktoren til fjernvarme følger utslippsfaktoren til strøm. 
                   I virkeligheten vil dette være avhengig av produksjonsmiksen til fjernvarme.''')
        ###
    with c3:
        st.caption("Alt 3)")
        st.write(f"**Energibrønner og solceller**")
        st.markdown("---")
        st.write("*Kjøpt strøm fra strømnettet*")
        name = 'Energibrønner'
        color = '#b7dc8f'
        if mode == 'hourly':
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_hourly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        else:
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_monthly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        st.markdown("---")
    with c4:
        st.caption("Alt 4)")
        st.write(f"**GeoTermos og solceller**")
        st.markdown("---")
        st.write("*Kjøpt strøm fra strømnettet*")
        #st.caption("Varme fra tørrkjøler eller PVT")
        if calculate_costs_object.selected_mode_charging_in_night:
            name = 'Termos og sol med lading om natten'
        else:
            name = 'Termos og sol'
        color = '#48a23f'
        if mode == 'hourly':
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_hourly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=-ymax_hourly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        else:
            show_simple_plot(df, name, color, ymin=0, ymax=ymax_monthly, mode=mode, hide_label='collapsed')
            st.markdown("---")
            st.write("*Solgt strøm*")
            show_simple_plot(df2, name, color, ymin=ymin_monthly, ymax=0, mode=mode, type='negative', hide_label='collapsed')
        st.markdown("---")
    st.info(''' 💡 Alternativet med fjernvarme og solceller må kjøpe minst 
            strøm fra strømnettet - men husk på at det her må kjøpes fjernvarme. 
            Ser vi på hele året vil 4) GeoTermos og solceller faktisk 
            bruke mer strøm enn 3) Energibrønner og solceller. 
            Det er viktig å ta i betraktning **når** man 
            bruker strømmen - her ser vi at GeoTermos bruker mindre 
            strøm om vinteren enn om sommeren.''')
    st.info(''' ❔ Lastprofilet til GeoTermos er veldig ulik de andre profilene. 
            Dette er fordi vi flytter last fra vinter til sommer. Dette vil være 
            gunstig med tanke på trendene med økt press på strømnettet om vinteren og derav
            mer varierende strømpriser med billigere priser om sommeren.''')

#######################################
#######################################
SCALE_FACTOR_DISTRICT_HEATING = calculate_costs_object.DISTRICT_HEATING_CO2

df_co2 = df.copy()
df2_co2 = df2.copy()
df_co2_imported = pd.read_excel('src/CO2.xlsx')
scaling = 1000 # kg
co2_array = np.array(list(df_co2_imported[calculate_costs_object.selected_co2]))
district_heating_co2_array = co2_array * SCALE_FACTOR_DISTRICT_HEATING
electric_columns = ['Termos og sol', 'Elkjel', 'Energibrønner', 'Termos og sol med lading om natten', 'Fjernvarme og sol - strøm']
district_heating_columns = ['Fjernvarme og sol - fjernvarme']

df_co2[electric_columns] = df_co2[electric_columns].apply(lambda row: apply_co2_scaling(row, co2_array, scaling), axis=1)
df2_co2[electric_columns] = df2_co2[electric_columns].apply(lambda row: apply_co2_scaling(row, co2_array, scaling), axis=1)
df_co2[district_heating_columns] = df_co2[district_heating_columns].apply(lambda row: apply_co2_scaling(row, district_heating_co2_array, scaling), axis=1)
df_co2['Fjernvarme og sol - totalt'] = df_co2['Fjernvarme og sol - strøm'] + df_co2['Fjernvarme og sol - fjernvarme']

ymax_hourly_co2 = df_co2['Elkjel'].max() * 1.1
ymax_monthly_co2 = np.max(hour_to_month(df_co2['Elkjel'].to_numpy())) * 1.1
ymin_hourly_co2 = np.min(df2_co2['Energibrønner']) * 1.1
ymin_monthly_co2 = np.min(hour_to_month(df2_co2['Energibrønner'].to_numpy())) * 1.1

with st.expander("CO₂ utslipp per år med bruk av strøm", expanded=False):
    st.write(f'''*Figurene viser CO₂ utslipp med strøm for de ulike alternativene med strøm fra {calculate_costs_object.selected_co2}.* ''')
    st.line_chart(df_co2_imported[calculate_costs_object.selected_co2], height=150, use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        name = 'Elkjel'
        color = '#1d3c34'
        st.caption("Alt 1)")
        st.write(f"**Elkjel og solceller**")
        if mode == 'hourly':
            reference_co2 = show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_hourly_co2, mode=mode, unit="kg CO₂")
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_hourly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        else:
            reference_co2 = show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_monthly_co2, mode=mode, unit="kg CO₂")
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_monthly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        st.markdown("---")
    with c2:
        st.caption("Alt 2)")
        st.write(f"**Fjernvarme og solceller**")
        name = 'Fjernvarme og sol - totalt'
        color = '#485738'
        if mode == 'hourly':
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_hourly_co2, mode=mode, unit="kg CO₂", reference_value=reference_co2)
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_hourly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        else:
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_monthly_co2, mode=mode, unit="kg CO₂", reference_value=reference_co2)
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_monthly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        st.markdown("---")
    with c3:
        st.caption("Alt 3)")
        st.write(f"**Energibrønner og solceller**")
        name = 'Energibrønner'
        color = '#b7dc8f'
        if mode == 'hourly':
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_hourly_co2, mode=mode, unit="kg CO₂", reference_value=reference_co2)
 #           st.markdown("---")
 #           show_simple_plot(df2_co2, name, color, ymin=ymin_hourly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        else:
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_monthly_co2, mode=mode, unit="kg CO₂", reference_value=reference_co2)
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_monthly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        st.markdown("---")
    with c4:
        st.caption("Alt 4)")
        st.write(f"**GeoTermos og solceller**")
        #st.caption("Varme fra tørrkjøler eller PVT")
        if calculate_costs_object.selected_mode_charging_in_night:
            name = 'Termos og sol med lading om natten'
        else:
            name = 'Termos og sol'
        color = '#48a23f'
        if mode == 'hourly':
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_hourly_co2, mode=mode, unit="kg CO₂")
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=-ymax_hourly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        else:
            show_simple_plot(df_co2, name, color, ymin=0, ymax=ymax_monthly_co2, mode=mode, unit="kg CO₂", reference_value=reference_co2)
#            st.markdown("---")
#            show_simple_plot(df2_co2, name, color, ymin=ymin_monthly_co2, ymax=0, mode=mode, type='negative', unit="kg CO₂")
        st.markdown("---")
    st.info(''' 💡 Både alternativ 3) og 4) vil redusere CO₂-utslippet 
            med bruk av strøm betraktelig sammenlignet med 1) og 2). 
            Utslipp til fjernvarme vil avhenge av fjernvarmens produksjonsmiks.''')

    #######################################
    #######################################
        
with st.expander("Kostnader", expanded=False):
    st.write(f'''*Figurene viser driftskostnader for de ulike alternativene basert på valgt strømpriser i menyen til venstre.* ''')
    c1, c2, c3, c4 = st.columns(4)        
    with c1:
        st.caption("Alt 1)")
        st.write(f"**Elkjel og solceller**")
        name = 'Elkjel'
        color = '#1d3c34'
        if mode == 'hourly':
            ymin = ymin_hourly*3
            ymax = ymax_hourly*4
        else:
            ymin = ymin_monthly*3
            ymax = ymax_monthly*4
        calculate_costs_object.forb = df_positive[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df, ymin=0, ymax=ymax, mode=mode)
        reference_cost = total_cost
        st.caption(f"Gjennomsnittlig strømkostnad {abs(round(total_cost/df[name].sum(),2)):,} kr/kWh".replace(".",","))
        st.markdown("---")
        calculate_costs_object.forb = df2[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df2, ymin=ymin, ymax=0, type='negative', nettleie_mode=False, mode=mode)
        st.caption(f"Gjennomsnittlig eksportpris for strøm {abs(round(total_cost/df2[name].sum(),2)):,} kr/kWh".replace(".",","))
    with c2:
        st.caption("Alt 2)")
        st.write(f"**Fjernvarme og solceller**")
        name = 'Fjernvarme og sol - totalt'
        color = '#485738'
        calculate_costs_object.forb = df_positive[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df, ymin=0, ymax=ymax, mode=mode, reference_value=reference_cost)
        st.caption(f"Gjennomsnittlig strømkostnad {abs(round(total_cost/df[name].sum(),2)):,} kr/kWh".replace(".",","))
        st.markdown("---")
        calculate_costs_object.forb = df2[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df2, ymin=ymin, ymax=0, type='negative', nettleie_mode=False, mode=mode)
        st.caption(f"Gjennomsnittlig eksportpris for strøm {abs(round(total_cost/df2[name].sum(),2)):,} kr/kWh".replace(".",","))
        with st.popover('Forenkling', use_container_width=True):
            st.write('''Det er gjort en forenkling om at fjernvarmeprisen følger strømprisen som er noenlunde sant i Norge. 
                   Det er lagt til rette for videre implementasjon av modeller for fjernvarmepris.''')
    with c3:
        st.caption("Alt 3)")
        st.write(f"**Energibrønner og solceller**")
        name = 'Energibrønner'
        color = '#b7dc8f'
        calculate_costs_object.forb = df_positive[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df, ymin=0, ymax=ymax, mode=mode, reference_value=reference_cost)
        st.caption(f"Gjennomsnittlig strømkostnad {abs(round(total_cost/df[name].sum(),2)):,} kr/kWh".replace(".",","))
        st.markdown("---")
        calculate_costs_object.forb = df2[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df2, ymin=ymin, ymax=0, type='negative', nettleie_mode=False, mode=mode)
        st.caption(f"Gjennomsnittlig eksportpris for strøm {abs(round(total_cost/df2[name].sum(),2)):,} kr/kWh".replace(".",","))
    with c4:
        st.caption("Alt 4)")
        st.write(f"**GeoTermos og solceller**")
        name = 'Termos og sol'
        color = '#48a23f'
        calculate_costs_object.forb = df_positive[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df, ymin=0, ymax=ymax, mode=mode, reference_value=reference_cost)
        st.caption(f"Gjennomsnittlig strømkostnad {abs(round(total_cost/df[name].sum(),2)):,} kr/kWh".replace(".",","))
        st.markdown("---")
        calculate_costs_object.forb = df2[name].to_numpy()
        total_cost = show_costs_plot(calculate_costs_object, df2, ymin=ymin, ymax=0, type='negative', nettleie_mode=False, mode=mode)
        st.caption(f"Gjennomsnittlig eksportpris for strøm {abs(round(total_cost/df2[name].sum(),2)):,} kr/kWh".replace(".",","))

    st.info(''' 💡 Ettersom lastprofilet til GeoTermos er veldig ulik de andre profilene 
            (vi flytter last fra vinter til sommer) vil GeoTermos være gunstig med tanke på 
            trendene med økt press på strømnettet om vinteren og derav
            mer varierende strømpriser med billigere priser om sommeren. Med sesongvarierende strømpriser 
            og økt nettleie ved høye effekttopper ser vi at GeoTermos er lønnsomt.''')
    #######################################
    #######################################


