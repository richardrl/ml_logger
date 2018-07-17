import React from 'react'
import {Flex, FlexItem} from 'layout-components';
import {
    XAxis,
    YAxis,
    VerticalGridLines,
    HorizontalGridLines,
    FlexibleWidthXYPlot,
    DiscreteColorLegend,
    Crosshair,
    LineSeries,
    LineSeriesCanvas  // use this for better performance.
} from 'react-vis';
import Highlight from './highlight';

class LineChartConfidence extends React.Component {
    state = {
        lastDrawLocation: null,
        crosshairValues: [],
        serieses: [],
    };

    static defaultProps = {
        serieses: [],
        legendWidth: null
    };

    componentWillMount() {
        const {serieses = []} = this.props;
        this.setState({serieses: serieses.map(l => ({...l}))})
    }

    componentWillReceiveProps(nextProps) {
        const {serieses = []} = nextProps;
        if (serieses !== this.props.serieses)
            this.setState({serieses: serieses.map(l => ({...l}))});
    }

    itemClick = (item, index) => {
        const {serieses} = this.state;
        item.disabled = !item.disabled;
        this.setState({serieses});
    };
    onMouseLeave = () => this.setState({crosshairValues: []});
    onNearestX = (lineKey) => (value, n) => {
        const {crosshairValues} = this.state;
        const lineIndex = crosshairValues.findIndex(({lineKey: _lineKey}) => _lineKey === lineKey);
        if (lineIndex > -1) {
            crosshairValues[lineIndex] = {...value, lineKey};
        } else {
            crosshairValues.push({...value, lineKey});
        }
        this.setState({crosshairValues})
    };
    onBrushEnd = (area) => this.setState({lastDrawLocation: area});

    render() {
        const {serieses, lastDrawLocation} = this.state;
        const {legendWidth, ...props} = this.props;
        delete props.serieses;
        return (
            <Flex row {...props}>
                <FlexItem>
                    <FlexibleWidthXYPlot
                        className="chart no-select"
                        animation
                        xDomain={lastDrawLocation && [lastDrawLocation.left, lastDrawLocation.right]}
                        width={200}
                        height={150}
                        onMouseLeave={this.onMouseLeave}
                    >
                        <HorizontalGridLines/>
                        <YAxis/>
                        <XAxis/>
                        {serieses.map((line) =>
                            <LineSeries key={line.title} data={line.disabled ? [] : line.data}
                                              onNearestX={this.onNearestX(line.title)}
                            />)}
                        <Crosshair values={this.state.crosshairValues}/>
                        <Highlight onBrushEnd={this.onBrushEnd}/>
                    </FlexibleWidthXYPlot>
                </FlexItem>
                <FlexItem style={{overflowY: 'auto'}} height={150}>
                    <DiscreteColorLegend width={legendWidth} items={serieses} onItemClick={this.itemClick}/>
                </FlexItem>
            </Flex>
        )
    }
}

export default LineChartConfidence;