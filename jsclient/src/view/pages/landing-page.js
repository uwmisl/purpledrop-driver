import ElectrodeBoard from '../components/electrode-board';
import {Pd} from '../../models/Pd';

export default function() {
    return {
        view() {
            return (
                <div>
                    <h2>Purple Drop</h2>
                    <p>On the fly drop control</p>
                    <ElectrodeBoard board={Pd.board} />
                </div>
            );
        },
    };
}